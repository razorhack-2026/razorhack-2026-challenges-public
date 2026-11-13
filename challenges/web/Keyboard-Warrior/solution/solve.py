#!/usr/bin/env python3
"""
Reference solver for MED BAY: Keyboard Warrior.

    python3 solve.py http://HOST:PORT

The server times each attempt from /api/level to /api/submit, so answering
immediately gives an absurd WPM. The catch: from level 4 the prompt contains
invisible zero-width characters that are not part of the expected text.
Echoing the prompt back verbatim costs ~3% accuracy and fails the final level.
"""
import re
import sys

import requests

INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060]")


def main():
    base = sys.argv[1].rstrip("/")
    s = requests.Session()
    s.post(f"{base}/api/start", json={}).raise_for_status()
    while True:
        lvl = s.post(f"{base}/api/level", json={}).json()
        if not lvl.get("ok"):
            print("error:", lvl)
            return 1
        text = INVISIBLE.sub("", lvl["prompt"])
        res = s.post(f"{base}/api/submit", json={"nonce": lvl["nonce"], "text": text}).json()
        print(f"level {lvl['level']}: {res.get('wpm')} WPM, {res.get('accuracy')}% ->",
              "passed" if res.get("passed") else res)
        if not res.get("passed"):
            return 1
        if res.get("flag"):
            print("FLAG:", res["flag"])
            return 0


if __name__ == "__main__":
    sys.exit(main())
