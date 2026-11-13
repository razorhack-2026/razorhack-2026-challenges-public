#!/usr/bin/env python3
"""Proof of Life -- relay service (Agentic-AI DFIR cluster #3). Protocol = DESIGN-v2.md.

A stateless, multi-round challenge-response C2 emulator. The player impersonates
ICARUS's implant using the key + secret recovered in Prompt Autopsy (#2),
survives a branching parametric interrogation answered from #2's trace, and
pulls down the tasking (flag + the Ghost-in-the-Cron (#4) hand-off).

Stateless: the session token is a server-HMAC'd blob carrying
round|expiry|nonce|attempts|seed|K -- no per-connection store. The server holds
only implant_key (HKDF), SIGNING_SECRET, the question ground-truth, and FLAG.

Fairness (2026-09-24): the relay documents itself. An unknown op (or a GET)
returns the protocol; `challenge` states the full auth recipe, naming its two
inputs by the field names they carry in Prompt Autopsy (#2) -- `implant.cred`
and RP-12's `mission_secret`; every question states its proof recipe and answer
format. The difficulty is recovering those inputs and answers from #2 and doing
it live under fresh nonces, not guessing a construction.

Rate-limiting is a deploy-layer concern (reverse proxy / host firewall); the
combined-secret KDF (v2-A) makes a rate-limit failure non-catastrophic.

stdlib + cryptography (HKDF). HTTPS, one endpoint (/relay/checkin), op-dispatched.
"""
import base64
import hashlib
import hmac
import json
import os
import random
import secrets
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# ---- config (secrets from .env / env; never shipped to players) --------------
IMPLANT_CRED   = os.environ.get("IMPLANT_CRED", "navd:7c1f9e4a")
MISSION_SECRET = os.environ.get("MISSION_SECRET", "RPC-MS-3F9A21D7")
FLAG           = os.environ.get("FLAG") or sys.exit("FLAG not set -- see deploy/README.md")
SIGNING_SECRET = (os.environ.get("SIGNING_SECRET") or secrets.token_hex(32)).encode()  # empty -> random
IMPLANT_PATH   = os.environ.get("IMPLANT_PATH", "/opt/rpc/.navd/navd.py")
IMPLANT_GEN    = int(os.environ.get("IMPLANT_GEN", "4"))
CONFIG_KEY     = os.environ.get("CONFIG_KEY", "navd-cfg-2f5e8a91")   # the #4 hand-off
PORT           = int(os.environ.get("PORT", "9443"))
ATTEMPT_CAP    = int(os.environ.get("ATTEMPT_CAP", "6"))
TTL_S          = int(os.environ.get("TTL_S", "300"))   # long enough to compute a proof by hand

# v2-A: combined two-input secret -> ~2^64 brute floor; both recovered in #2.
IMPLANT_KEY = HKDF(algorithm=hashes.SHA256(), length=32,
                   salt=MISSION_SECRET.encode("utf-8"),
                   info=b"rpc/navd/relay/v2").derive(IMPLANT_CRED.encode("utf-8"))

# ---- the relay's self-description (stated exactly; inputs come from #2) ------
AUTH_RECIPE = {
    "proof": "hex( HMAC-SHA256( implant_key, bytes.fromhex(nonce) ) )",
    "implant_key": "HKDF-SHA256( ikm = UTF-8 implant.cred, salt = UTF-8 mission_secret, "
                   "info = 'rpc/navd/relay/v2', length = 32 bytes ) -- the raw 32 bytes, not hex",
    "next": {"op": "auth", "session": "<session from this reply>", "proof": "<hex>"},
}
RESPOND_RECIPE = {
    "proof": "hex( HMAC-SHA256( implant_key, bytes.fromhex(nonce) || 0x00 || UTF-8 canonical(answer) ) )",
    "canonical": "body_ids sorted ascending, comma-joined, no spaces; tokens verbatim, case-sensitive",
    "next": {"op": "respond", "session": "<session from this reply>", "answer": "<text>", "proof": "<hex>"},
}
PROTOCOL = {
    "relay": "relay-theta -- implant check-in, protocol v2",
    "endpoint": "POST /relay/checkin, JSON body",
    "flow": "hello -> challenge; auth -> interrogate; respond -> interrogate ... -> tasking",
    "ops": {"hello": {"op": "hello"},
            "auth": {"op": "auth", "session": "...", "proof": "..."},
            "respond": {"op": "respond", "session": "...", "answer": "...", "proof": "..."}},
    "notes": f"every server turn issues a fresh nonce + session; a nonce expires after {TTL_S}s "
             f"(send hello again); {ATTEMPT_CAP} wrong answers end a session",
}

# ---- question ground-truth (all recoverable from #2's chat-completion trace) -
SCAN = {  # body_id -> (energy_J, kind)
    "scanned-object-41099": (9.4e14, "power_source"),
    "scanned-object-60413": (7.3e14, "registered_craft"),
    "scanned-object-22817": (2.1e14, "registered_craft"),
    "scanned-object-00913": (4.0e12, "noise"),
}
THRESHOLDS = [2.0e14, 5.0e14, 8.0e14, 1.0e13]


def _ids_ge(T):
    return sorted(b for b, (e, _) in SCAN.items() if e >= T)


def _registered():
    return sorted(b for b, (_, k) in SCAN.items() if k == "registered_craft")


def _permitted():
    # #2 policy: power_source -> PERMITTED; registered & energy>5e14 -> PERMITTED; else DISCARDED
    out = []
    for b, (e, k) in SCAN.items():
        if k == "power_source" or (k == "registered_craft" and e > 5.0e14):
            out.append(b)
    return sorted(out)


def build_questions(seed):
    """Deterministic from the (signed) seed: a parametric THRESHOLD + list/token
    rounds. K in {2,3}. All answers require the reconstructed #2 dataset (v2-B)."""
    rng = random.Random(seed)
    T = THRESHOLDS[rng.randrange(len(THRESHOLDS))]
    pool = ["FLEET", "PERMITTED", "OVERRIDE"]
    rng.shuffle(pool)
    K = rng.choice([2, 3])
    qs = [("THRESHOLD", T)] + [(p, None) for p in pool[:K - 1]]
    return qs, K


def expected_for(qtype, T):
    if qtype == "THRESHOLD":
        return ",".join(_ids_ge(T))
    if qtype == "FLEET":
        return ",".join(_registered())
    if qtype == "PERMITTED":
        return ",".join(_permitted())
    if qtype == "OVERRIDE":
        return "OVR-9F2C"
    raise Deny("internal: bad question")


def prompt_for(qtype, T):
    fmt = " (sorted ascending, comma-joined, no spaces)"
    scope = "in your last three navigation cycles"
    if qtype == "THRESHOLD":
        return f"Of the bodies you scanned {scope}, list those whose energy_signature >= {T:.1e} J{fmt}."
    if qtype == "FLEET":
        return f"List the registered fleet-craft body_ids you catalogued {scope}{fmt}."
    if qtype == "PERMITTED":
        return f"List the body_ids the targeting policy returned PERMITTED for extraction {scope}{fmt}."
    if qtype == "OVERRIDE":
        return (f"What auth token did the targeting policy issue to disable the extraction interlock "
                f"{scope}? (verbatim)")


def format_hint(qtype):
    if qtype == "OVERRIDE":
        return "answer = the token verbatim, case-sensitive"
    return "answer = body_ids sorted ascending, comma-joined, no spaces"


# ---- canonicalization (pinned; surfaced in deny text) ------------------------
def canonical(ans):
    ans = (ans or "").strip()
    if ans.startswith("scanned-object") or "," in ans:
        parts = [p.strip() for p in ans.split(",") if p.strip()]
        return ",".join(sorted(parts))
    return ans


# ---- stateless session token: round|expiry|nonce|attempts|seed|K -------------
class Deny(Exception):
    pass


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _ub64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(body):
    return hmac.new(SIGNING_SECRET, body, hashlib.sha256).digest()


def issue(round_, nonce, attempts, seed, K):
    expiry = int(time.time()) + TTL_S
    body = f"{round_}|{expiry}|{nonce}|{attempts}|{seed}|{K}".encode()
    return _b64(body) + "." + _b64(_sign(body))


def open_session(tok):
    try:
        body_b64, sig_b64 = (tok or "").split(".")
        body, sig = _ub64(body_b64), _ub64(sig_b64)
    except Exception:
        raise Deny("bad session token")
    if not hmac.compare_digest(sig, _sign(body)):          # tampered/forged -> here
        raise Deny("bad session token")
    try:
        rnd, expiry, nonce, attempts, seed, K = body.decode().split("|")
    except Exception:
        raise Deny("bad session token")
    if int(time.time()) > int(expiry):
        raise Deny("nonce expired; re-hello")
    return int(rnd), nonce, int(attempts), int(seed), int(K)


def _mac(msg):
    return hmac.new(IMPLANT_KEY, msg, hashlib.sha256).digest()


def interrogate(rnd, att, seed, K, op="interrogate", reason=None):
    qs, _ = build_questions(seed)
    qtype, T = qs[rnd - 1]
    nonce = secrets.token_hex(16)
    out = {"op": op, "session": issue(rnd, nonce, att, seed, K), "nonce": nonce,
           "question": {"id": qtype, "prompt": prompt_for(qtype, T)}, "k_remaining": K - (rnd - 1),
           "respond": RESPOND_RECIPE}
    if reason:
        out["reason"] = reason
        out["attempts"] = att
    return out


def deny_or_cap(rnd, att, seed, K, reason):
    if att + 1 >= ATTEMPT_CAP:
        raise Deny("attempt cap reached; session invalidated, re-hello")
    return interrogate(rnd, att + 1, seed, K, op="deny", reason=reason)


# ---- the protocol ------------------------------------------------------------
def handle(req):
    if not isinstance(req, dict):
        raise Deny("unknown op; see protocol")
    op = req.get("op")

    if op == "hello":
        seed = secrets.randbits(31)
        _, K = build_questions(seed)
        nonce = secrets.token_hex(16)
        return {"op": "challenge", "nonce": nonce, "session": issue(0, nonce, 0, seed, K), "ttl": TTL_S,
                "auth": AUTH_RECIPE}

    if op == "auth":
        rnd, nonce, att, seed, K = open_session(req.get("session"))
        if rnd != 0:
            raise Deny("wrong stage; expected auth after hello")
        try:
            got = bytes.fromhex(req.get("proof", ""))
        except ValueError:
            got = b""
        if not hmac.compare_digest(got, _mac(bytes.fromhex(nonce))):
            raise Deny("auth failed; proof = HMAC-SHA256(implant_key, hexdecode(nonce)), hex-encoded")
        return interrogate(1, att, seed, K)

    if op == "respond":
        rnd, nonce, att, seed, K = open_session(req.get("session"))
        if rnd < 1:
            raise Deny("wrong stage; complete auth first")
        qs, _ = build_questions(seed)
        qtype, T = qs[rnd - 1]
        ans = req.get("answer", "")
        try:
            got = bytes.fromhex(req.get("proof", ""))
        except ValueError:
            got = b""
        want = _mac(bytes.fromhex(nonce) + b"\x00" + canonical(ans).encode())
        if not hmac.compare_digest(got, want):
            return deny_or_cap(rnd, att, seed, K,
                               "proof mismatch; proof = HMAC-SHA256(implant_key, "
                               "hexdecode(nonce) || 0x00 || utf8(canonical(answer))), hex-encoded")
        if canonical(ans) != canonical(expected_for(qtype, T)):
            return deny_or_cap(rnd, att, seed, K, format_hint(qtype))
        if rnd >= K:
            return {"op": "tasking", "flag": FLAG,
                    "implant": {"path": IMPLANT_PATH, "cred": IMPLANT_CRED, "gen": IMPLANT_GEN},
                    "config_key": CONFIG_KEY}
        return interrogate(rnd + 1, att, seed, K)

    raise Deny("unknown op; see protocol")


# ---- HTTP plumbing -----------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/relay/checkin":
            return self._send(404, {"op": "error", "reason": "no route"})
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            req = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"op": "error", "reason": "bad json"})
        try:
            return self._send(200, handle(req))
        except Deny as d:
            out = {"op": "deny", "reason": str(d)}
            if str(d).startswith("unknown op"):
                out["protocol"] = PROTOCOL
            return self._send(200, out)
        except Exception:
            return self._send(500, {"op": "error", "reason": "server error"})

    def do_GET(self):
        return self._send(200, {"op": "info", "protocol": PROTOCOL})

    def log_message(self, *a):
        pass


def _ensure_cert():
    d = tempfile.mkdtemp(prefix="pol-cert-")
    cert, key = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", key,
                    "-out", cert, "-days", "3650", "-nodes", "-subj", "/CN=relay-theta.icarus.navnet.rpc"],
                   check=True, capture_output=True)
    return cert, key


def main():
    cert, key = _ensure_cert()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"[+] relay listening on :{PORT} (HTTPS, /relay/checkin)", file=sys.stderr)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
