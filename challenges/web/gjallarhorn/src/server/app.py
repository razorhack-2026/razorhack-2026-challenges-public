"""Gjallarhorn validator + static host. One stateless container.

POST /api/check   {"code": "..."} or {"token": "..."}  -> {"ok": bool}      (60/min/IP)
POST /api/purge   {"code","token","nodes":[...]}       -> verdict           (burst 10, 60/10min/IP)
Everything else is the compiled console (static files). No storage, no shell-out.
"""
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("KEYS_DIR", os.path.join(HERE, "..")))
import launch_token  # noqa: E402

with open(os.path.join(HERE, "secret.json")) as f:
    SECRET = json.load(f)
INFECTED = frozenset(SECRET["infected"])
FLAG = os.environ.get("FLAG", "flag{placeholder_set_FLAG_env}")
STATIC = os.environ.get("STATIC_DIR", os.path.join(HERE, "static"))
TRUST_PROXY = int(os.environ.get("TRUST_PROXY", "0"))   # reverse proxies in front of us; 0 = none
MAX_NODES = 200
PRUNE_AT = 5000   # per-IP rate-limit maps are swept of idle keys above this size

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


def client_ip():
    if TRUST_PROXY:
        hops = [h.strip() for h in request.headers.get("X-Forwarded-For", "").split(",") if h.strip()]
        if len(hops) >= TRUST_PROXY:
            return hops[-TRUST_PROXY]   # each of our proxies appends the peer it saw; count from the right
    return request.remote_addr or "?"


class Window:
    """Sliding window: at most `n` hits per `secs` per key."""

    def __init__(self, n, secs):
        self.n, self.secs, self.h = n, secs, defaultdict(deque)

    def hit(self, key):
        """0 if allowed, else seconds until the next slot frees up."""
        now = time.monotonic()
        if len(self.h) > PRUNE_AT:
            for k in [k for k, v in self.h.items() if not v or now - v[-1] > self.secs]:
                del self.h[k]
        q = self.h[key]
        while q and now - q[0] > self.secs:
            q.popleft()
        if len(q) >= self.n:
            return max(1, int(q[0] + self.secs - now) + 1)
        q.append(now)
        return 0


class Bucket:
    """Token bucket: burst `cap`, refilled so that `per` tokens accrue each `secs`."""

    def __init__(self, cap, per, secs):
        self.cap, self.rate, self.s = cap, per / secs, {}

    def take(self, key):
        """0 if allowed, else seconds until a token is available."""
        now = time.monotonic()
        if len(self.s) > PRUNE_AT:   # idle keys have refilled to full; dropping them is lossless
            full = self.cap / self.rate
            for k in [k for k, (_, t) in self.s.items() if now - t > full]:
                del self.s[k]
        tok, last = self.s.get(key, (self.cap, now))
        tok = min(self.cap, tok + (now - last) * self.rate)
        if tok < 1:
            self.s[key] = (tok, now)
            return max(1, int((1 - tok) / self.rate) + 1)
        self.s[key] = (tok - 1, now)
        return 0


check_limit = Window(60, 60)          # code/token checks: 60 per minute per IP
purge_limit = Bucket(10, 60, 600)     # purge: burst 10, then 60 per 10 minutes per IP


def too_many(wait):
    r = jsonify(error="rate limited", retryAfter=wait)
    r.status_code = 429
    r.headers["Retry-After"] = str(wait)
    return r


def norm_code(s):
    return re.sub(r"[\s\-]+", "", str(s)).lower()


def code_ok(s):
    return hashlib.sha256(norm_code(s).encode()).hexdigest() == SECRET["code_sha256"]


def token_ok(s):
    return isinstance(s, str) and len(s) < 512 and launch_token.verify_token(s)


@app.post("/api/check")
def check():
    wait = check_limit.hit(client_ip())
    if wait:
        return too_many(wait)
    j = request.get_json(silent=True) or {}
    if "code" in j:
        return jsonify(ok=code_ok(j["code"]))
    if "token" in j:
        return jsonify(ok=token_ok(j["token"]))
    return jsonify(ok=False)


@app.post("/api/purge")
def purge():
    wait = purge_limit.take(client_ip())
    if wait:
        return too_many(wait)
    j = request.get_json(silent=True) or {}
    nodes = j.get("nodes")
    if not (isinstance(nodes, list) and len(nodes) <= MAX_NODES and all(isinstance(n, str) for n in nodes)):
        return jsonify(status="rejected"), 400
    if not (code_ok(j.get("code", "")) and token_ok(j.get("token", ""))):
        return jsonify(status="unauthorized"), 403
    if set(nodes) == INFECTED:
        return jsonify(status="neutralized", flag=FLAG)
    return jsonify(status="incomplete")      # identical for every wrong set


@app.get("/", defaults={"path": "index.html"})
@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(STATIC, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
