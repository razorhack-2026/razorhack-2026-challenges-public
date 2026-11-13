#!/usr/bin/env python3
"""
Hosted calibration panel: the same puzzle as dist/calibration_sequence, played
in a browser.

The puzzle lives here, not in the page. Each player gets their own panel, keyed
by a cookie, and the page only draws the dot positions this server sends. The
flag is unsealed by rubik2d.reveal_flag once that panel is actually solved, so
FLAG_SEALED and the keystream never reach the browser.

Run:  python3 server.py          (PORT defaults to 8082; needs only numpy)
"""
import json
import os
import random
import secrets
import sys
import threading
from collections import OrderedDict
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from rubik2d import (CENTRES, MOVES, RADII, SEED, START_IMAGE, Cube, moving, parse,  # noqa: E402
                     reveal_flag, rotation, scramble, sticker_xy, turn_sense)

COOKIE = "panel"
MAX_SESSIONS = 4096  # oldest panels are dropped past this
MAX_MOVES = 400      # per request
MAX_BODY = 8192


def read(path):
    with open(path, "rb") as f:
        return f.read()


# Everything servable, loaded once: no request path ever reaches the filesystem.
STATIC = {
    "/": ("text/html; charset=utf-8", read(os.path.join(HERE, "static", "index.html"))),
    "/panel.js": ("text/javascript; charset=utf-8", read(os.path.join(HERE, "static", "panel.js"))),
    "/target.png": ("image/png", read(START_IMAGE)),
}

sessions = OrderedDict()  # token -> Cube, least recently used first
lock = threading.Lock()


def scrambled():
    cube = Cube()
    for name, q in scramble(rng=random.Random(SEED)):  # every game starts scrambled
        cube.apply(name, q)
    return cube


def point(xy):
    return [round(float(v), 5) for v in xy]


def dot_gap():
    """Smallest distance between two dots, which the page sizes its dots from."""
    xy = np.array([sticker_xy(p, n) for p, n in Cube().stickers])
    d = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(len(xy)) * 1e9
    return float(d.min())


LAYOUT = {"centres": [point(c) for c in CENTRES], "radii": list(RADII), "gap": dot_gap()}


def turn_of(cube, name, q):
    """How each dot travels during a move, for the page to animate (the same
    paths as Scene.draw). Call before applying the move."""
    axis = MOVES[name][0]
    total = MOVES[name][2] * q
    snap = np.rint(rotation(axis, total)).astype(int)
    dots = []
    for (pos, n), col in cube.stickers.items():
        q0 = sticker_xy(pos, n)
        dot = {"from": point(q0), "to": point(q0), "col": col}
        if moving(pos, name):
            q1 = sticker_xy(tuple(int(v) for v in snap @ pos), tuple(int(v) for v in snap @ n))
            pivot = sticker_xy(n, n) if n[axis] else CENTRES[axis]
            dot.update(to=point(q1), pivot=point(pivot), sense=float(turn_sense(axis, total, n)))
        dots.append(dot)
    return dots


def state_of(cube):
    solved = cube.solved()
    state = {"dots": [{"xy": point(sticker_xy(p, n)), "col": col} for (p, n), col in cube.stickers.items()],
             "solved": solved}
    if solved:
        state["flag"] = reveal_flag(cube)
    return state


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "RASA"
    sys_version = ""
    timeout = 30

    def panel(self):
        """This player's token and cube, creating them if needed. Call with the
        lock held."""
        token = None
        try:
            morsel = SimpleCookie(self.headers.get("Cookie", "")).get(COOKIE)
            token = morsel.value if morsel else None
        except CookieError:
            pass
        if token not in sessions:
            token = self.new_token = secrets.token_hex(16)
            sessions[token] = scrambled()
            while len(sessions) > MAX_SESSIONS:
                sessions.popitem(last=False)
        sessions.move_to_end(token)
        return token, sessions[token]

    def reply(self, status, ctype, body):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        token = getattr(self, "new_token", None)
        if token:
            self.send_header("Set-Cookie", f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax")
            self.new_token = None
        self.end_headers()
        self.wfile.write(body)

    def json(self, obj, status=200):
        self.reply(status, "application/json", json.dumps(obj).encode())

    def reject(self, message, status=400):
        self.close_connection = True  # any unread body must not parse as a request
        self.json({"error": message}, status)

    def body(self):
        """The request's JSON object, or None if it isn't one."""
        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 <= length <= MAX_BODY:
                return None
            data = json.loads(self.rfile.read(length))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            with lock:
                _, cube = self.panel()
                state = state_of(cube)
            self.json({"layout": LAYOUT, **state})
        elif path in STATIC:
            self.reply(200, *STATIC[path])
        else:
            self.reject("not found", 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/new":
            self.rfile.read(min(int(self.headers.get("Content-Length") or 0), MAX_BODY))
            with lock:
                token, _ = self.panel()
                sessions[token] = cube = scrambled()
                state = state_of(cube)
            self.json(state)
        elif path == "/api/moves":
            data = self.body()
            moves = data.get("moves") if data else None
            if not isinstance(moves, str):
                return self.reject('expected {"moves": "..."}')
            try:
                seq = parse(moves)
            except ValueError as e:
                return self.reject(str(e))
            if len(seq) > MAX_MOVES:
                return self.reject(f"at most {MAX_MOVES} moves per request")
            with lock:
                _, cube = self.panel()
                turn = turn_of(cube, *seq[0]) if len(seq) == 1 else None
                for name, q in seq:
                    cube.apply(name, q)
                state = state_of(cube)
            self.json({"turn": turn, **state})
        else:
            self.reject("not found", 404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8082"))
    print(f"calibration panel on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
