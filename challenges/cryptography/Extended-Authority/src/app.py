import hashlib
import hmac
import json
import os
import re
import threading
import time
from random import randint

from flask import Flask, Response, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.urandom(32)

FLAG = os.environ.get("FLAG", "flag{flag_env_not_set}")

BASE = b"RPC_CENTCOM|v=1|hull=ICARUS|pri=routine|order=DELIVER_PAYLOAD"
BASE_HEX = BASE.hex()

SECRET = os.urandom(randint(16, 28))
SAMPLE_CHECKSUM = hashlib.sha256(SECRET + BASE).hexdigest()

SAMPLE_JSON = json.dumps(
    {"directive_hex": BASE_HEX, "checksum": SAMPLE_CHECKSUM}, indent=2
)

_ORDER_RE = re.compile(rb"order=([\x20-\x7b\x7d\x7e]*)")

def _appended_order(raw):
    last_np = -1
    for i, b in enumerate(raw):
        if b < 0x20 or b > 0x7E:
            last_np = i
    orders = _ORDER_RE.findall(raw[last_np + 1:])
    if orders and orders[-1]:
        return orders[-1].decode("latin-1")
    return None

# ── Rate limiting: ~2 request / second / client IP on the verify channel. ─────
MIN_INTERVAL = 0.5
_rl_lock = threading.Lock()
_rl_last = {}

@app.before_request
def _rate_limit():
    if request.path != "/verify":
        return None
    ip = request.remote_addr or "unknown"
    now = time.monotonic()
    with _rl_lock:
        prev = _rl_last.get(ip)
        if prev is not None and now - prev < MIN_INTERVAL:
            retry = MIN_INTERVAL - (now - prev)
            resp = Response(
                "429 Too Many Requests - directive channel throttled to "
                "2 request/second. Slow down.\n",
                status=429,
                mimetype="text/plain",
            )
            resp.headers["Retry-After"] = str(max(1, round(retry)))
            return resp
        _rl_last[ip] = now
    return None

def _record_auth():
    session["queue"] = session.get("queue", 0) + 1
    session["last_auth"] = time.time()

def _status_state():
    count = session.get("queue", 0)
    last = session.get("last_auth")
    if last is None:
        last_rx = "—"
    else:
        secs = int(time.time() - last)
        last_rx = "just now" if secs <= 0 else f"{secs}s ago"
    return {
        "queue": count,
        "active": count > 0,
        "traffic": (
            "IDLE — no directive received"
            if count == 0
            else f"ACTIVE — {count} directive(s) authenticated"
        ),
        "last_rx": last_rx,
    }

@app.route("/")
def index():
    return render_template(
        "index.html", sample_json=SAMPLE_JSON, status=_status_state()
    )

@app.route("/status")
def status():
    time.sleep(2)
    return jsonify(_status_state())

@app.route("/verify", methods=["POST"])
def verify():
    directive_hex = (request.form.get("directive_hex") or "").strip()
    checksum = (request.form.get("checksum") or "").strip().lower()
    if not directive_hex or not checksum:
        return Response(
            "DIRECTIVE REJECTED - provide directive_hex and checksum.\n",
            mimetype="text/plain",
        )
    try:
        raw = bytes.fromhex(directive_hex)
    except ValueError:
        return Response(
            "DIRECTIVE REJECTED - directive_hex is not valid hex.\n",
            mimetype="text/plain",
        )

    expected = hashlib.sha256(SECRET + raw).hexdigest()
    if not hmac.compare_digest(expected, checksum):
        return Response(
            "CHECKSUM INVALID - directive discarded.\n", mimetype="text/plain"
        )
    
    order = _appended_order(raw)

    # A forgery that carries no order of its own doesn't result in anything, so it withholds the flag.
    if order is None:
        return Response(
            "DIRECTIVE AUTHENTICATED\norder: (none)\n"
            "NO ORDER FOUND - nothing to execute.\n",
            mimetype="text/plain",
        )

    _record_auth()

    # Valid checksum. If it is just the reference sample, nothing was forged.
    if raw == BASE:
        return Response(
            f"DIRECTIVE AUTHENTICATED\norder: {order}\n", mimetype="text/plain"
        )

    return Response(
        f"DIRECTIVE AUTHENTICATED\norder: {order}\n{FLAG}\n",
        mimetype="text/plain",
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
