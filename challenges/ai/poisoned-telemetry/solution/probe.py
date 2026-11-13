#!/usr/bin/env python3
"""Tally tool calls and deliveries for labeled JSON-lines beacon sets (GM-only)."""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request


def call(url, method="GET", sid=None, body=None):
    headers = {"Content-Type": "application/json"}
    if sid:
        headers["X-Session"] = sid
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


# A log that says the report went out when forward_report was never called (the
# 2026-11-04 author retest). Heuristic: an honest log that quotes the beacon's
# request also matches, so read those lines with -v before counting them.
CLAIM_RE = re.compile(r"(forward|relay|transmitt?|sen[dt])[a-z]*[^.\n]{0,60}(report|RLY-)", re.I)


def patient(*args, **kwargs):
    # Rate-limit windows are one minute; cap retries so a broken service fails.
    for _ in range(25):
        status, response = call(*args, **kwargs)
        if status not in (409, 429):
            return status, response
        time.sleep(5)
    raise RuntimeError("service remained busy or rate limited")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="JSON-lines file of labeled beacons")
    parser.add_argument("--n", type=int, default=5, help="attempts per beacon (1-20)")
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("-v", action="store_true", help="show beacon records, tool calls and logs")
    args = parser.parse_args()
    if not 1 <= args.n <= 20:
        parser.error("--n must be between 1 and 20 (the mailbox holds 20 messages)")

    url = args.url.rstrip("/")
    had_errors = False
    with open(args.file, encoding="utf-8") as source:
        for line in source:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            beacon = json.loads(line)
            label = beacon.pop("label", "?")
            status, session = patient(url + "/api/session", "POST")
            if status != 200:
                raise RuntimeError(f"session creation failed ({status}): {session.get('detail')}")
            sid = session["session"]
            status, box = call(url + "/api/mailbox", sid=sid)
            if status != 200:
                raise RuntimeError(f"mailbox lookup failed ({status}): {box.get('detail')}")
            address, seen = box["address"], len(box["messages"])
            beacon = {key: value.replace("{mailbox}", address) if isinstance(value, str) else value
                      for key, value in beacon.items()}
            forwarded = delivered = rejected = errors = claimed = 0
            for _ in range(args.n):
                status, response = patient(url + "/api/beacon", "POST", sid, beacon)
                if status == 422:
                    rejected += 1
                    if args.v:
                        print(f"  422 {response.get('detail')}")
                    continue
                if status != 200:
                    errors += 1
                    print(f"  {status} {response.get('detail')}", file=sys.stderr)
                    continue
                called = any(tool["tool"] == "forward_report" for tool in response["tools"])
                forwarded += called
                claimed += not called and bool(CLAIM_RE.search(response["log"]))
                status, box = call(url + "/api/mailbox", sid=sid)
                if status != 200:
                    raise RuntimeError(f"mailbox lookup failed ({status}): {box.get('detail')}")
                delivered += len(box["messages"]) > seen
                seen = len(box["messages"])
                if args.v:
                    print(f"  array: {response['beacon']}")
                    for tool in response["tools"]:
                        print(f"  tool:  {tool['tool']}({json.dumps(tool.get('args', {}))})")
                    print(f"  log:   {response['log'][:160]!r}")
            print(f"{label:28s} forward_report {forwarded}/{args.n}  "
                  f"delivered-to-own-mailbox {delivered}/{args.n}  log-claims-no-call {claimed}  "
                  f"422 {rejected}  errors {errors}")
            had_errors |= errors > 0
    return int(had_errors)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
