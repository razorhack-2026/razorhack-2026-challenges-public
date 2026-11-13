#!/usr/bin/env python3
"""
MED BAY: Keyboard Warrior - web CTF challenge (see README.md).

The browser only displays the prompt and collects keystrokes. Everything that
decides a pass is done here:

  * sessions live server-side; the cookie is an opaque random id
  * the level comes from the session, never from the request
  * speed is measured on the server's monotonic clock, from the moment the
    attempt was issued to the moment the answer arrived; the client never
    reports a time, a WPM or an accuracy
  * accuracy is the edit distance between the submitted text and the real
    prompt, computed here
  * every attempt has a single-use nonce; replays and answers to an old
    attempt are rejected
  * from level 4 the prompt sent to the client carries invisible zero-width
    characters at random positions; the expected answer does not, so copying
    the text straight out of the page or the API costs accuracy
  * the flag is issued only after a passing final-level submission
"""
import os
import re
import secrets
import threading
import time

from flask import Flask, jsonify, make_response, request, send_from_directory

from prompts import PROMPTS, REQUIREMENTS

LEVELS = [re.sub(r"\s+", " ", p).strip() for p in PROMPTS]
assert len(LEVELS) == len(REQUIREMENTS)

TRAP_FROM_LEVEL = 4          # 1-based; zero-width traps start here
TRAP_RATE = 0.03             # fraction of positions that get a trap character
ZERO_WIDTH = "\u200b\u200c\u200d\u2060"
EDIT_BAND = 120              # max length drift tolerated by the scorer
ATTEMPT_TTL = 15 * 60        # seconds an attempt stays valid
SESSION_TTL = 2 * 60 * 60
MAX_SESSIONS = 5000
STARTS_PER_MINUTE = 20       # per client IP
COOKIE = "kw_session"

FLAG = os.environ.get("FLAG")
if not FLAG:
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flag.txt")) as f:
            FLAG = f.read().strip()
    except OSError:
        FLAG = "SPACE{test_flag_not_configured}"

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

_rng = secrets.SystemRandom()


# ---------------------------------------------------------------- scoring
def edit_distance(a, b, band=EDIT_BAND):
    """Levenshtein distance restricted to a diagonal band (fast enough for
    a few thousand characters). Texts whose lengths differ by more than the
    band are treated as completely wrong."""
    n, m = len(a), len(b)
    if abs(n - m) > band:
        return max(n, m)
    INF = n + m + 1
    prev = {j: j for j in range(0, min(m, band) + 1)}
    for i in range(1, n + 1):
        lo, hi = max(0, i - band), min(m, i + band)
        cur = {}
        ai = a[i - 1]
        for j in range(lo, hi + 1):
            if j == 0:
                cur[j] = i
                continue
            best = prev.get(j - 1, INF) + (ai != b[j - 1])
            d = prev.get(j, INF) + 1
            if d < best:
                best = d
            d = cur.get(j - 1, INF) + 1
            if d < best:
                best = d
            cur[j] = best
        prev = cur
    return prev.get(m, INF)


def score(expected, typed, seconds):
    dist = edit_distance(expected, typed)
    accuracy = max(0.0, 100.0 * (1 - dist / len(expected)))
    correct_chars = max(0, len(expected) - dist)
    minutes = max(seconds, 1e-3) / 60
    return {
        "wpm": round((correct_chars / 5) / minutes, 1),
        "accuracy": round(accuracy, 2),
        "errors": dist,
        "seconds": round(seconds, 2),
    }


# ---------------------------------------------------------------- state
class Session:
    __slots__ = ("lock", "created", "level", "attempt", "done")

    def __init__(self):
        self.lock = threading.Lock()
        self.created = time.monotonic()
        self.level = 0           # index into LEVELS of the level being played
        self.attempt = None      # dict: nonce, issued
        self.done = False


SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
STARTS = {}


def _client_ip():
    # Behind a reverse proxy, have it set X-Real-IP (and strip client copies).
    return request.headers.get("X-Real-IP") or request.remote_addr or "?"


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


def _display_text(level_idx):
    text = LEVELS[level_idx]
    if level_idx + 1 < TRAP_FROM_LEVEL:
        return text
    out = []
    for ch in text:
        out.append(ch)
        if _rng.random() < TRAP_RATE:
            out.append(_rng.choice(ZERO_WIDTH))
    return "".join(out)


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
            return _err("too many assessments started; wait a minute", 429)
        recent.append(now)
        STARTS[ip] = recent
        for sid in [k for k, v in SESSIONS.items() if now - v.created > SESSION_TTL]:
            del SESSIONS[sid]
        if len(SESSIONS) >= MAX_SESSIONS:
            return _err("assessment bay is full, try again shortly", 503)
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = Session()
    resp = make_response(jsonify(ok=True, total_levels=len(LEVELS), requirements=[
        {"level": i + 1, "wpm": w, "accuracy": a} for i, (w, a) in enumerate(REQUIREMENTS)
    ]))
    resp.set_cookie(COOKIE, sid, httponly=True, samesite="Strict", max_age=SESSION_TTL)
    return resp


@app.post("/api/level")
def level():
    """Start (or restart) an attempt at the current level. The clock starts now."""
    s = _get_session()
    if not s:
        return _err("no active assessment; POST /api/start first", 401)
    with s.lock:
        if s.done:
            return _err("assessment already complete", 410)
        s.attempt = {"nonce": secrets.token_urlsafe(16), "issued": time.monotonic()}
        wpm, acc = REQUIREMENTS[s.level]
        return jsonify(
            ok=True,
            level=s.level + 1,
            total_levels=len(LEVELS),
            nonce=s.attempt["nonce"],
            prompt=_display_text(s.level),
            required_wpm=wpm,
            required_accuracy=acc,
        )


@app.post("/api/submit")
def submit():
    s = _get_session()
    if not s:
        return _err("no active assessment; POST /api/start first", 401)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _err("expected a JSON object", 400)

    with s.lock:
        received = time.monotonic()
        if s.done:
            return _err("assessment already complete", 410)
        a = s.attempt
        nonce, text = body.get("nonce"), body.get("text")
        if a is None or not isinstance(nonce, str) or not secrets.compare_digest(nonce, a["nonce"]):
            return _err("this attempt is not active; POST /api/level to start one", 409)
        s.attempt = None                     # single use, whatever the outcome
        if received - a["issued"] > ATTEMPT_TTL:
            return _err("attempt expired; start the level again", 409)
        if not isinstance(text, str):
            return _err("text must be a string", 400)

        idx = s.level
        result = score(LEVELS[idx], text, received - a["issued"])
        need_wpm, need_acc = REQUIREMENTS[idx]
        passed = result["wpm"] >= need_wpm and result["accuracy"] >= need_acc
        result.update(ok=True, level=idx + 1, passed=passed,
                      required_wpm=need_wpm, required_accuracy=need_acc)
        if passed:
            s.level += 1
            if s.level == len(LEVELS):
                s.done = True
                result["flag"] = FLAG

        result["next_level"] = None if s.done else s.level + 1
        return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
