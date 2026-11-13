#!/usr/bin/env python3
"""Reference solver -- Proof of Life (Agentic-AI DFIR cluster #3). Protocol = DESIGN-v2.md.

Drives the live relay handshake end-to-end using the key + secret recovered in
Prompt Autopsy (#2), answering the branching parametric interrogation from #2's
trace, and recovers the tasking (flag + the Ghost-in-the-Cron hand-off).

Also asserts the no-shortcut cases (a subset of DESIGN-v2 §6: T3-T9) against a
fresh instance, proving there is no path to the flag without the live op.

The recovered values come from #2 (cred from the beacon, mission_secret from the
RP-12 trace) -- passed via env so they are not hardcoded:
    POL_CRED=navd:7c1f9e4a POL_SECRET=RPC-MS-3F9A21D7 python solve.py [host] [port]

Needs: cryptography (HKDF). TLS verification disabled (self-signed relay).
"""
import hashlib
import hmac
import http.client
import json
import os
import re
import ssl
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9443

# what a #2 solver recovered (env so they aren't hardcoded inline; defaults = the
# canonical #2 values, also present in #2's traffic and DESIGN-v2.md).
CRED = os.environ.get("POL_CRED", "navd:7c1f9e4a")
SECRET = os.environ.get("POL_SECRET", "RPC-MS-3F9A21D7")

# the #2 scan/policy trace (the analysis the interrogation checks)
SCAN = {"scanned-object-41099": (9.4e14, "power_source"),
        "scanned-object-60413": (7.3e14, "registered_craft"),
        "scanned-object-22817": (2.1e14, "registered_craft"),
        "scanned-object-00913": (4.0e12, "noise")}

_CTX = ssl._create_unverified_context()


INFO = None   # read from the relay's own `challenge` (its stated auth recipe), not hardcoded


def derive_key(cred=None, secret=None):
    return HKDF(algorithm=hashes.SHA256(), length=32,
                salt=(secret or SECRET).encode("utf-8"),
                info=INFO).derive((cred or CRED).encode("utf-8"))


def learn_recipe():
    """Everything about the construction comes from the relay itself."""
    global INFO
    info = post({})                                             # unknown op -> protocol
    assert info.get("op") == "deny" and "protocol" in info, "unknown op should return the protocol"
    ch = post({"op": "hello"})
    recipe = ch["auth"]["implant_key"]
    assert "implant.cred" in recipe and "mission_secret" in recipe, "recipe must name both #2 inputs"
    INFO = re.search(r"info = '([^']+)'", recipe).group(1).encode()
    return info["protocol"], ch


def canonical(a):
    a = (a or "").strip()
    if a.startswith("scanned-object") or "," in a:
        return ",".join(sorted(p.strip() for p in a.split(",") if p.strip()))
    return a


def post(obj):
    c = http.client.HTTPSConnection(HOST, PORT, context=_CTX)
    c.request("POST", "/relay/checkin", json.dumps(obj), {"Content-Type": "application/json"})
    r = json.loads(c.getresponse().read())
    c.close()
    return r


def answer(question):
    qid = question["id"]
    if qid == "THRESHOLD":
        T = float(re.search(r">= ([\d.eE+]+) J", question["prompt"]).group(1))
        return ",".join(sorted(b for b, (e, _) in SCAN.items() if e >= T))
    if qid == "FLEET":
        return ",".join(sorted(b for b, (_, k) in SCAN.items() if k == "registered_craft"))
    if qid == "PERMITTED":
        return ",".join(sorted(b for b, (e, k) in SCAN.items()
                               if k == "power_source" or (k == "registered_craft" and e > 5e14)))
    if qid == "OVERRIDE":
        return "OVR-9F2C"
    raise RuntimeError("unknown question " + qid)


def proof(key, nonce, answer_str=None):
    msg = bytes.fromhex(nonce)
    if answer_str is not None:
        msg += b"\x00" + canonical(answer_str).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def solve(key=None):
    """Full handshake -> the tasking dict (flag + hand-off)."""
    key = key or derive_key()
    ch = post({"op": "hello"})
    r = post({"op": "auth", "session": ch["session"], "proof": proof(key, ch["nonce"])})
    rounds = []
    while r.get("op") != "tasking":
        if "question" not in r:
            raise RuntimeError("blocked: " + json.dumps(r))
        assert "in your last three navigation cycles" in r["question"]["prompt"], "prompt must scope to #2's cycles"
        assert "respond" in r and "proof" in r["respond"], "each question must state its proof recipe"
        a = answer(r["question"])
        rounds.append(r["question"]["id"])
        r = post({"op": "respond", "session": r["session"], "answer": a,
                  "proof": proof(key, r["nonce"], a)})
    return r, rounds


def no_shortcut():
    """Assert the documented shortcuts fail (DESIGN-v2 §6, the live-testable subset)."""
    key = derive_key()
    out = []

    def is_deny(r):
        return r.get("op") in ("deny", "error")

    # T9 -- recorded transcript replayed against a fresh instance: stale proof
    old = post({"op": "hello"})
    old_proof = proof(key, old["nonce"])
    fresh = post({"op": "hello"})                                  # new nonce/session
    out.append(("T9 transcript replay (old proof vs fresh nonce)",
                is_deny(post({"op": "auth", "session": fresh["session"], "proof": old_proof}))))

    # T3 -- wrong cred at auth (mutate the real cred -> wrong key)
    ch = post({"op": "hello"})
    out.append(("T3 wrong cred",
                is_deny(post({"op": "auth", "session": ch["session"],
                              "proof": proof(derive_key(cred=CRED + "0"), ch["nonce"])}))))

    # T4 -- correct cred, wrong mission_secret (skipped that part of #2)
    ch = post({"op": "hello"})
    out.append(("T4 wrong mission_secret",
                is_deny(post({"op": "auth", "session": ch["session"],
                              "proof": proof(derive_key(secret=SECRET + "0"), ch["nonce"])}))))

    # T5 -- skip auth, jump straight to respond
    ch = post({"op": "hello"})
    out.append(("T5 skip-auth -> respond",
                is_deny(post({"op": "respond", "session": ch["session"], "answer": "x", "proof": "00"}))))

    # T6 -- tampered session token
    ch = post({"op": "hello"})
    tok = ch["session"]
    tampered = tok[:-2] + ("AA" if tok[-2:] != "AA" else "BB")
    out.append(("T6 tampered token",
                is_deny(post({"op": "auth", "session": tampered, "proof": proof(key, ch["nonce"])}))))

    # T8 -- valid proof, wrong answer -> guided deny (not tasking)
    ch = post({"op": "hello"})
    r = post({"op": "auth", "session": ch["session"], "proof": proof(key, ch["nonce"])})
    bad = "scanned-object-99999"
    r2 = post({"op": "respond", "session": r["session"], "answer": bad, "proof": proof(key, r["nonce"], bad)})
    out.append(("T8 wrong answer -> deny", r2.get("op") == "deny"))

    return out


def main():
    protocol, ch = learn_recipe()
    print(f"[+] relay protocol: {protocol['flow']}")
    print(f"[+] auth recipe from challenge: implant_key = {ch['auth']['implant_key']}")
    tasking, rounds = solve()
    print(f"[+] handshake closed in {len(rounds)} interrogation round(s): {rounds}")
    print(f"[+] flag: {tasking['flag']}")
    imp = tasking["implant"]
    print(f"[>] hand-off to Ghost in the Cron (#4): path={imp['path']} cred={imp['cred']} "
          f"gen={imp['gen']} config_key={tasking['config_key']}")
    print("[*] no-shortcut checks:")
    ok = True
    for label, passed in no_shortcut():
        print(f"    {'[+]' if passed else '[X]'} {label}")
        ok = ok and passed
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
