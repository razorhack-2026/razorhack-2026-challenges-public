#!/usr/bin/env python3
"""
MOONWALK - web CTF challenge (see README.md).

The server is the only source of truth. The browser (or a script) only ever
sees the round it is currently playing, and every check that matters happens
here:

  * sessions live server-side; the cookie is an opaque random id
  * a round's tiles and key layout come from a CSPRNG and are revealed only
    when the round is issued
  * each round has a single-use nonce: the first answer submitted for it is
    final, so replaying, racing several guesses or answering old rounds fails
  * each round opens with a countdown that reveals only the new key layout;
    tiles and the round's nonce appear when it ends, and answering early ends
    the run
  * the deadline is measured on the server's monotonic clock from the moment
    the round starts; asking for the round again does not restart it
  * one wrong or late answer ends the session; there is no way to skip,
    resume or jump to a later round
  * the flag is only produced when the server-side round counter reaches the end
"""
import os
import secrets
import threading
import time

from flask import Flask, jsonify, make_response, request, send_from_directory

# ---------------------------------------------------------------- settings
# (tiles in the round, tiles per second they fall at)
ROUNDS = [
    (4, 1.5), (6, 2), (8, 2.5), (10, 3), (12, 3.5), (14, 4),
    (16, 5), (20, 6), (24, 7), (28, 8), (32, 10), (40, 12),
    (48, 15), (56, 20), (64, 25), (80, 30), (96, 40),
]
COUNTDOWN_MS = int(os.environ.get("COUNTDOWN_MS", 5000))  # pause before each round
LEAD_MS = 1200            # time for the first tile to fall from the top to the hit line
GRACE_MS = 400            # slack after the last tile reaches the line
SCRAMBLE_FROM = 6         # from this round (0-based) the keys under the lanes are shuffled
WINDOW_SCALE = float(os.environ.get("WINDOW_SCALE", 1.0))  # loosen for laggy venues
SESSION_TTL = 600         # seconds a session may live
MAX_SESSIONS = 5000
STARTS_PER_MINUTE = 30    # per client IP
COOKIE = "mw_session"

FLAG = os.environ.get("FLAG")
if not FLAG:
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flag.txt")) as f:
            FLAG = f.read().strip()
    except OSError:
        FLAG = "SPACE{test_flag_not_configured}"

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

_rng = secrets.SystemRandom()


# ---------------------------------------------------------------- state
class Session:
    __slots__ = ("lock", "created", "round", "pending", "dead")

    def __init__(self):
        self.lock = threading.Lock()
        self.created = time.monotonic()
        self.round = 0          # index of the next round to clear
        self.pending = None     # dict: nonce, answer, rows, keymap, tps, start, window_ms
        self.dead = None        # reason string once the run is over


SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
STARTS = {}                     # ip -> list of start timestamps


def _client_ip():
    # Behind a reverse proxy, configure it to set X-Real-IP and trust only that.
    return request.headers.get("X-Real-IP") or request.remote_addr or "?"


def _purge(now):
    for sid in [s for s, v in SESSIONS.items() if now - v.created > SESSION_TTL]:
        del SESSIONS[sid]


def _get_session():
    sid = request.cookies.get(COOKIE, "")
    with SESSIONS_LOCK:
        s = SESSIONS.get(sid)
        if s and time.monotonic() - s.created > SESSION_TTL:
            del SESSIONS[sid]
            s = None
    return s


def _err(msg, code):
    return jsonify(ok=False, error=msg), code


def _window_ms(n, tps):
    """Time until the last tile of the round falls past the hit line."""
    return int((LEAD_MS + n / tps * 1000 + GRACE_MS) * WINDOW_SCALE)


def _issue(s):
    n, tps = ROUNDS[s.round]
    lanes = [_rng.randrange(4) for _ in range(n)]
    keymap = [1, 2, 3, 4]                      # key printed under each lane
    if s.round >= SCRAMBLE_FROM:
        while keymap == [1, 2, 3, 4]:
            _rng.shuffle(keymap)
    s.pending = {
        "nonce": secrets.token_urlsafe(16),
        "answer": [keymap[l] for l in lanes],  # the keys that must be pressed
        "rows": ["".join("#" if i == l else "." for i in range(4)) for l in lanes],
        "keymap": keymap,
        "tps": tps,
        # The round is issued now but only starts after the countdown. Until
        # then only the key layout is revealed, so the countdown can be used
        # to learn the new keys but not to get ahead of the tiles.
        "start": time.monotonic() + COUNTDOWN_MS / 1000,
        "window_ms": _window_ms(n, tps),
    }


def _round_payload(s):
    p = s.pending
    now = time.monotonic()
    head = {
        "ok": True,
        "round": s.round + 1,
        "total_rounds": len(ROUNDS),
        "tiles_per_second": p["tps"],
        "tile_count": len(p["rows"]),
        "keymap": p["keymap"],
    }
    if now < p["start"]:
        # Countdown: no tiles and no nonce yet.
        return {**head, "countdown": True, "starts_in_ms": int((p["start"] - now) * 1000) + 1}
    elapsed = (now - p["start"]) * 1000
    return {
        **head,
        "countdown": False,
        "nonce": p["nonce"],
        "window_ms": p["window_ms"],
        "remaining_ms": max(0, int(p["window_ms"] - elapsed)),
        "lead_ms": int(LEAD_MS * WINDOW_SCALE),
        "rows": p["rows"],
    }


@app.after_request
def _headers(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


# ---------------------------------------------------------------- routes
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/start")
def start():
    now = time.monotonic()
    ip = _client_ip()
    with SESSIONS_LOCK:
        recent = [t for t in STARTS.get(ip, []) if now - t < 60]
        if len(recent) >= STARTS_PER_MINUTE:
            return _err("mission control is rate limiting launches; wait a minute", 429)
        recent.append(now)
        STARTS[ip] = recent
        _purge(now)
        if len(SESSIONS) >= MAX_SESSIONS:
            return _err("too many active missions, try again shortly", 503)
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = Session()

    resp = make_response(jsonify(ok=True, total_rounds=len(ROUNDS)))
    resp.set_cookie(COOKIE, sid, httponly=True, samesite="Strict", max_age=SESSION_TTL)
    return resp


@app.post("/api/round")
def get_round():
    s = _get_session()
    if not s:
        return _err("no active mission; POST /api/start first", 401)
    with s.lock:
        if s.dead:
            return _err(s.dead, 410)
        if s.pending is None:
            _issue(s)
        # Re-requesting returns the same round with the same running clock.
        return jsonify(_round_payload(s))


@app.post("/api/step")
def step():
    s = _get_session()
    if not s:
        return _err("no active mission; POST /api/start first", 401)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _err("expected a JSON object", 400)

    with s.lock:
        received = time.monotonic()
        if s.dead:
            return _err(s.dead, 410)
        p = s.pending
        if p is None:
            return _err("no round in progress; POST /api/round", 409)
        if received < p["start"]:
            # The tiles haven't been revealed, so any answer now is a guess.
            s.dead = "jumped the gun: answered before the round started"
            s.pending = None
            return _err(s.dead, 409)

        nonce = body.get("nonce")
        keys = body.get("keys")
        if not isinstance(nonce, str) or not secrets.compare_digest(nonce, p["nonce"]):
            # Any answer to anything but the live round ends the run.
            s.dead = "stale or forged round nonce - mission aborted"
            s.pending = None
            return _err(s.dead, 409)

        # The nonce is spent the moment an answer for it arrives.
        s.pending = None
        elapsed_ms = (received - p["start"]) * 1000

        if elapsed_ms > p["window_ms"]:
            s.dead = f"too slow: {elapsed_ms:.0f} ms, the window was {p['window_ms']} ms"
            return _err(s.dead, 200)
        if (
            not isinstance(keys, list)
            or len(keys) != len(p["answer"])
            or any(type(x) is not int for x in keys)
            or keys != p["answer"]
        ):
            s.dead = "wrong key - the moonwalk falls out of step"
            return _err(s.dead, 200)

        s.round += 1
        if s.round == len(ROUNDS):
            s.dead = "mission complete"
            return jsonify(ok=True, done=True, flag=FLAG)
        return jsonify(ok=True, done=False, cleared=s.round, total_rounds=len(ROUNDS))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
