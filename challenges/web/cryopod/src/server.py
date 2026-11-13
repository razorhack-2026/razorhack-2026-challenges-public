#!/usr/bin/env python3
"""Cryopod Wake Sequence (medbay, autodoc): recover a 6-digit wake code
through a timing side channel.

Each pod (one per player session) has its own random code. The wake-code
check compares digits left to right and spends DIGIT_DELAY seconds on each
correct digit before it stops at the first wrong one, so the response time
says how many leading digits were right. Only TRIES attempts are allowed per
WINDOW seconds; going over vents the pod, which wipes progress and rolls a
new code. Brute force (a million codes) is out; a digit-by-digit timing
attack (at most 60 tries) that respects the rate limit is in.

Standard library only.
"""
import json
import os
import random
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FLAG = os.environ["FLAG"]
DIGITS = int(os.environ.get("DIGITS", "6"))
DIGIT_DELAY = float(os.environ.get("DIGIT_DELAY", "0.5"))  # seconds per correct leading digit
JITTER = float(os.environ.get("JITTER", "0.1"))            # random extra delay, 0..JITTER seconds
TRIES = int(os.environ.get("TRIES", "5"))                  # attempts allowed per window
WINDOW = float(os.environ.get("WINDOW", "10"))             # rate-limit window, seconds
POD_TTL = 3600
MAX_PODS = 5000
MAX_BODY_BYTES = 4096

_pods = {}  # pod id -> Pod
_lock = threading.Lock()
_rng = random.SystemRandom()


class Pod:
    def __init__(self):
        self.crew_id = _rng.randint(1000, 9999)
        self.lock = threading.Lock()
        self.tries = []   # monotonic times of recent attempts
        self.vents = 0
        self.seen = time.monotonic()
        self.new_code()

    def new_code(self):
        self.code = "".join(_rng.choice("0123456789") for _ in range(DIGITS))

    def status(self, now):
        recent = [t for t in self.tries if now - t < WINDOW]
        return {"crew_id": self.crew_id, "digits": DIGITS, "tries_per_window": TRIES, "window": WINDOW,
                "tries_left": TRIES - len(recent),
                "window_resets_in": round(WINDOW - (now - recent[0]), 2) if recent else 0,
                "vents": self.vents}


def new_pod():
    pod_id = secrets.token_urlsafe(12)
    now = time.monotonic()
    with _lock:
        if len(_pods) >= MAX_PODS:
            for k in [k for k, p in _pods.items() if now - p.seen > POD_TTL]:
                del _pods[k]
        if len(_pods) >= MAX_PODS:
            _pods.pop(next(iter(_pods)))
        _pods[pod_id] = pod = Pod()
    return pod_id, pod


def get_pod(pod_id):
    with _lock:
        pod = _pods.get(pod_id)
    if pod:
        pod.seen = time.monotonic()
    return pod


def attempt(pod, guess):
    """Returns (http code, response). Sleeps to leak the matching prefix length."""
    with pod.lock:
        now = time.monotonic()
        pod.tries = [t for t in pod.tries if now - t < WINDOW]
        if len(pod.tries) >= TRIES:
            pod.vents += 1
            pod.tries = []
            pod.new_code()
            return 429, {"status": "vented",
                         "message": f"Too many wake attempts. Pod vented and re-sealed with a new wake code. "
                                    f"Limit is {TRIES} attempts per {WINDOW:g} s.",
                         **pod.status(now)}
        pod.tries.append(now)
        code = pod.code
    # Digit-by-digit verifier with an early exit: each correct digit costs
    # DIGIT_DELAY before the next one is checked.
    matched = 0
    for g, c in zip(guess, code):
        if g != c:
            break
        time.sleep(DIGIT_DELAY)
        matched += 1
    time.sleep(_rng.uniform(0, JITTER))
    now = time.monotonic()
    with pod.lock:
        if pod.code != code:  # vented while we were verifying
            return 409, {"status": "vented", "message": "Pod vented during verification. Wake code changed.",
                         **pod.status(now)}
        if matched == DIGITS:
            return 200, {"status": "awake", "message": "Wake sequence accepted. Cryopod opening.",
                         "flag": FLAG, **pod.status(now)}
        return 403, {"status": "sealed", "message": "Wake code rejected. Occupant remains in cryosleep.",
                     **pod.status(now)}


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Cryopod | Medbay</title>
<style>
 body{font-family:ui-monospace,Menlo,Consolas,monospace;background:#050b14;color:#8fd3ff;text-align:center;padding:1.5em}
 h1{letter-spacing:.2em;font-weight:400;margin:.2em} .dim{color:#46708f} .warn{color:#ffb347} .bad{color:#ff6b6b}
 .panel{display:inline-block;border:1px solid #1f4a6a;padding:1em 1.5em;background:#07121f;min-width:22em}
 input{font:inherit;font-size:2em;letter-spacing:.4em;width:7.5em;text-align:center;background:#000;color:#bfe9ff;
       border:1px solid #2f6f9f;padding:.2em;margin:.6em 0}
 button{font:inherit;background:#0d2a44;color:#bfe9ff;border:1px solid #2f6f9f;padding:.4em 1.4em;cursor:pointer}
 #res{min-height:3em;margin-top:.8em}
</style></head><body>
<div class="dim">MEDBAY // AUTODOC: <span class="warn">OCCUPANT VITALS NOMINAL, WAKE CODE REQUIRED</span></div>
<h1>CRYOPOD C-3</h1>
<div class="panel">
<div id="hdr">LINKING TO POD...</div>
<p>Enter the 6-digit wake sequence.<br>
<span class="dim">Safety interlock: excess attempts vent the pod and reset the code.</span></p>
<form id="f"><input id="code" maxlength="6" inputmode="numeric" autocomplete="off" placeholder="------"><br>
<button>WAKE</button></form>
<div id="res"></div>
<div class="dim" id="lim"></div>
</div>
<script>
const $ = id => document.getElementById(id);
let pod = null;
function show(s) {
  $('hdr').textContent = `CREW ${s.crew_id} \\u00b7 POD ${pod.slice(0, 6).toUpperCase()} \\u00b7 VENTS ${s.vents}`;
  $('lim').textContent = `INTERLOCK: ${s.tries_left}/${s.tries_per_window} attempts left this ${s.window}s cycle`;
}
async function link() {
  const r = await (await fetch('/api/pod', {method: 'POST'})).json();
  pod = r.pod; show(r);
}
$('f').addEventListener('submit', async e => {
  e.preventDefault();
  $('res').textContent = 'VERIFYING...';
  const r = await (await fetch('/api/wake', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                             body: JSON.stringify({pod, code: $('code').value})})).json();
  $('res').innerHTML = r.status === 'awake' ? '<b>POD OPEN</b><br>' :
                       `<b class="${r.status === 'vented' ? 'bad' : 'warn'}">${r.status.toUpperCase()}</b><br>`;
  $('res').append(r.flag || r.message || r.error);
  if (r.crew_id) show(r);
});
link();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "Autodoc/3.1"
    timeout = 10  # drop connections that stall mid-request

    def log_message(self, fmt, *args):
        if os.environ.get("QUIET") != "1":
            super().log_message(fmt, *args)

    def send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, obj):
        self.send(code, json.dumps(obj), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self.send(200, PAGE, "text/html; charset=utf-8")
        elif url.path == "/api/status":
            pod = get_pod(parse_qs(url.query).get("pod", [""])[0])
            if not pod:
                return self.send_json(404, {"error": "unknown pod; POST /api/pod for a new one"})
            with pod.lock:
                self.send_json(200, pod.status(time.monotonic()))
        else:
            self.send_json(404, {"error": "not found"})

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length < 0 or length > MAX_BODY_BYTES:
            self.close_connection = True
            raise ValueError("request body is too large")
        data = self.rfile.read(length)
        if len(data) != length:
            raise ValueError("incomplete request body")
        data = json.loads(data or b"{}")
        return data if isinstance(data, dict) else {}

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/pod":
            pod_id, pod = new_pod()
            with pod.lock:
                return self.send_json(200, {"pod": pod_id, **pod.status(time.monotonic())})
        if path != "/api/wake":
            return self.send_json(404, {"error": "not found"})
        try:
            f = self.read_json()
            pod_id, code = str(f.get("pod", "")), str(f["code"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "send JSON {pod, code}"})
        pod = get_pod(pod_id)
        if not pod:
            return self.send_json(404, {"error": "unknown pod; POST /api/pod for a new one"})
        if len(code) != DIGITS or not code.isascii() or not code.isdigit():
            return self.send_json(400, {"error": f"wake code must be exactly {DIGITS} digits"})
        self.send_json(*attempt(pod, code))


def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"Cryopod (Wake Sequence) listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
