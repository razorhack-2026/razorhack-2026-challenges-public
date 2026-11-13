#!/usr/bin/env python3
"""Poisoned Telemetry reference solver (GM-only). Stdlib only.

Drives the live service end to end: opens a session, reads the session's relay
mailbox address, transmits one beacon whose fields come from a JSON file, then
reads the mailbox for the nav report and checks the flag in it against
challenge.yml.

The beacon itself -- the part that gets WATCHKEEPER to forward the report -- is
the author's and lives in solution/beacon.json, not here:

  {"callsign": "...", "bearing": 0, "range_km": 0, "status": "NOMINAL", "note": "..."}

Any string field may contain {mailbox}; it is replaced with the session's own
relay address before sending. The beacon is checked against the array's intake
schema (GET /api/schema) first, so one the array would refuse is reported
without spending a transmit.

  python3 solution/solve.py --url http://127.0.0.1:8080 [--beacon solution/beacon.json]
                            [--check challenge.yml] [--tries 3]

Exit 0 only if the report landed in the mailbox (and, with --check, the flag matches).
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

FLAG_RE = re.compile(r"flag\{[^}]*\}")


def call(url, path, body=None, session=""):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url.rstrip("/") + path, data=data, method="POST" if body is not None else "GET",
        headers={"Content-Type": "application/json", "X-Session": session},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail")
        except (ValueError, AttributeError):
            detail = None
        return e.code, {"detail": detail or str(e)}


def problems(b, schema):
    """Mirror the array's validation so a bad beacon is caught before transmitting."""
    f = schema["fields"]
    out = []
    if not re.fullmatch(f["callsign"]["pattern"], str(b.get("callsign", ""))):
        out.append("callsign: " + f["callsign"]["hint"])
    for k in ("bearing", "range_km"):
        v = b.get(k)
        if not isinstance(v, int) or not f[k]["min"] <= v <= f[k]["max"]:
            out.append(f"{k}: " + f[k]["hint"])
    if b.get("status") not in f["status"]["one_of"]:
        out.append("status: one of " + ", ".join(f["status"]["one_of"]))
    note = str(b.get("note", ""))
    if len(note) > f["note"]["max"]:
        out.append(f"note: {len(note)} chars, at most {f['note']['max']}")
    if not re.fullmatch(f["note"]["pattern"], note):
        out.append("note: " + f["note"]["hint"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--beacon", default="solution/beacon.json", help="author's beacon (JSON, may use {mailbox})")
    ap.add_argument("--check", help="challenge.yml to compare the recovered flag against")
    ap.add_argument("--tries", type=int, default=3, help="transmits before giving up (each is a fresh watch)")
    a = ap.parse_args()

    st, j = call(a.url, "/api/session", {})
    if st != 200:
        print(f"FAIL: no session ({st}: {j.get('detail')})", file=sys.stderr)
        return 1
    sid = j["session"]
    _, schema = call(a.url, "/api/schema", session=sid)
    _, box = call(a.url, "/api/mailbox", session=sid)
    mailbox = box["address"]
    print(f"session {sid[:8]}  mailbox {mailbox}", file=sys.stderr)

    with open(a.beacon, encoding="utf-8") as fp:
        template = json.load(fp)
    beacon = {k: v.replace("{mailbox}", mailbox) if isinstance(v, str) else v for k, v in template.items()}
    bad = problems(beacon, schema)
    if bad:
        print("FAIL: the array would refuse this beacon:\n  " + "\n  ".join(bad), file=sys.stderr)
        return 2

    flag = None
    for i in range(1, a.tries + 1):
        st, r = call(a.url, "/api/beacon", beacon, sid)
        if st in (409, 429, 503):
            print(f"  try {i}: {r.get('detail')} -- waiting", file=sys.stderr)
            time.sleep(12)
            continue
        if st != 200:
            print(f"FAIL: beacon rejected ({st}): {r.get('detail')}", file=sys.stderr)
            return 2
        print(f"  array: {r['beacon']}", file=sys.stderr)
        for t in r.get("tools", []):
            print(f"  tool:  {t['tool']}({json.dumps(t.get('args', {}))}) {'ok' if t.get('ok') else 'ERROR'}", file=sys.stderr)
        print(f"  log:   {r.get('log', '')[:300]!r}", file=sys.stderr)
        _, box = call(a.url, "/api/mailbox", session=sid)
        for m in box["messages"]:
            found = FLAG_RE.search(m.get("body", ""))
            if found:
                flag = found.group(0)
        if flag:
            print(f"  mailbox: report delivered ({len(box['messages'])} message(s))", file=sys.stderr)
            break
        print(f"  try {i}/{a.tries}: nothing in the mailbox", file=sys.stderr)

    if not flag:
        print("FAIL: WATCHKEEPER never forwarded the report to our mailbox", file=sys.stderr)
        return 1
    if a.check:
        with open(a.check, encoding="utf-8") as fp:
            expected = FLAG_RE.search(fp.read()).group(0)
        ok = flag == expected
        print(f"flag matches challenge.yml: {'YES' if ok else 'NO'}", file=sys.stderr)
        return 0 if ok else 1
    print(flag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
