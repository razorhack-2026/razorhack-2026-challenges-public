#!/usr/bin/env python3
"""Odd Pixel (medbay, CT-7): find the one voxel in a CT density slice that
differs from the rest, in under 5 seconds.

Standard library only. Each challenge gets a fresh image, a fresh odd pixel and a
single-use token; the 5-second window is enforced server-side.
"""
import base64
import json
import os
import random
import secrets
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FLAG = os.environ["FLAG"]
WIDTH = int(os.environ.get("WIDTH", "512"))
HEIGHT = int(os.environ.get("HEIGHT", "512"))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", "5"))
MAX_DELTA = int(os.environ.get("MAX_DELTA", "3"))  # how many grey levels the odd voxel is off by
MAX_PENDING = 10000
MAX_BODY_BYTES = 4096

_pending = {}  # token -> (x, y, issued_at)
_lock = threading.Lock()


def encode_png(width, height, rows):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + row for row in rows)  # filter type 0 on every row
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def make_challenge():
    rng = random.SystemRandom()
    # Greyscale "tissue density": one random grey, with one voxel a tiny bit off.
    # Invisible to the eye, obvious to a script.
    grey = rng.randint(40 + MAX_DELTA, 200 - MAX_DELTA)
    base = [grey] * 3
    odd = [grey + rng.choice([-1, 1]) * rng.randint(1, MAX_DELTA)] * 3
    x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)

    row = bytes(base) * WIDTH
    odd_row = row[:3 * x] + bytes(odd) + row[3 * x + 3:]
    rows = [odd_row if i == y else row for i in range(HEIGHT)]
    png = encode_png(WIDTH, HEIGHT, rows)

    token = secrets.token_urlsafe(16)
    now = time.monotonic()
    with _lock:
        if len(_pending) >= MAX_PENDING:
            for t in [t for t, v in _pending.items() if now - v[2] > TIME_LIMIT]:
                del _pending[t]
        if len(_pending) >= MAX_PENDING:
            _pending.pop(next(iter(_pending)))
        _pending[token] = (x, y, now)
    return token, png


def check_answer(token, x, y):
    with _lock:
        entry = _pending.pop(token, None)  # single use, right or wrong
    if entry is None:
        return False, "Unknown or already used token. Fetch a new slice."
    ox, oy, issued = entry
    if time.monotonic() - issued > TIME_LIMIT:
        return False, f"Exposure window closed. You have {TIME_LIMIT:g} seconds."
    if (x, y) != (ox, oy):
        return False, "Healthy tissue at that voxel. Wrong pixel."
    return True, FLAG


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>CT-7 | Medbay</title>
<style>
 body{font-family:ui-monospace,Menlo,Consolas,monospace;background:#05100f;color:#7fe0c8;text-align:center;padding:1.5em;margin:0;min-height:100vh;box-sizing:border-box}
 h1{letter-spacing:.2em;font-weight:400;margin:.2em} .dim{color:#3f8f7f} .warn{color:#ffb347}
 .panel{display:inline-block;border:1px solid #1f5f55;padding:1.2em;background:#071a18;max-width:100%;box-sizing:border-box}
 .workbench{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:1.25em;align-items:start}
 .task{min-width:0;text-align:center}.reference{width:250px;text-align:left;padding:.8em;border:1px solid #17473f;background:#061512;box-sizing:border-box}
 .reference h2{font-weight:400;font-size:1em;letter-spacing:.12em;margin:.5em 0}
 .scan-window{position:relative;overflow:hidden;background:#000;border:1px solid #2f8f7f}
 .scan-window.chest{height:230px}.scan-window img{position:absolute;width:153%;max-width:none;height:auto;left:-26.5%;top:50%;transform:translateY(-50%);border:0;margin:0}
 #img{border:1px solid #2f8f7f;cursor:crosshair;image-rendering:pixelated;display:block;margin:.8em auto;background:#000}
 #t{font-size:1.8em;font-variant-numeric:tabular-nums} a{color:#9ff} #res{min-height:1.4em}
 @media(max-width:950px){.workbench{grid-template-columns:1fr}.reference{width:100%;max-width:512px;margin:0 auto}.scan-window.chest{height:230px}}
</style></head><body>
<div class="dim">MEDBAY // AUTODOC: <span class="warn">BELOW DETECTION THRESHOLD, MANUAL READ</span></div>
<h1>CT-7 SCANNER</h1>
<div class="panel">
<div class="workbench"><section class="task">
<div id="hdr">ACQUIRING SLICE...</div>
<p>CT-7 has flagged an anomaly in the scan.<br>
Complete the diagnostic before the dose limit closes the exposure window.</p>
<div>EXPOSURE WINDOW <span id="t" class="warn">-</span> s</div>
<img id="img" alt="CT-7 two-dimensional density map">
<div id="res"></div>
<div class="dim">[ <a href="#" id="next">next slice</a> ]</div>
</section><aside class="reference">
<div class="dim">PATIENT FILE // MEDICAL RECORD</div><h2>CHEST SCAN</h2>
<div class="scan-window chest"><img src="/static/chest-scan.png" alt="Chest X-ray from the patient file"></div>
<p class="dim">CT-7 patient record.</p>
</aside></div>
</div>
<script>
const $ = id => document.getElementById(id);
let token = null, raf = 0;
async function load() {
  cancelAnimationFrame(raf); $('res').textContent = ''; $('img').style.opacity = 1;
  const c = await (await fetch('/api/challenge')).json();
  token = c.token;
  $('hdr').textContent = `CREW ${c.crew_id} \u00b7 SLICE ${c.slice} \u00b7 DENSITY MAP`;
  $('img').width = c.width; $('img').height = c.height;
  $('img').src = 'data:image/png;base64,' + c.image;
  const start = performance.now();
  const tick = () => {
    const r = Math.max(0, c.time_limit - (performance.now() - start) / 1000);
    $('t').textContent = r.toFixed(1);
    if (r > 0) raf = requestAnimationFrame(tick); else $('img').style.opacity = .15;
  };
  tick();
}
$('img').addEventListener('click', async e => {
  if (!token) return;
  const img = e.currentTarget, b = img.getBoundingClientRect();
  const x = Math.floor(e.clientX - b.left - img.clientLeft), y = Math.floor(e.clientY - b.top - img.clientTop);
  const t = token; token = null; cancelAnimationFrame(raf);
  const r = await (await fetch('/api/submit', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                               body: JSON.stringify({token: t, x, y})})).json();
  $('res').innerHTML = r.success ? '<b>ANOMALY CONFIRMED</b> ' : '<b class="warn">READ REJECTED</b> ';
  $('res').append(r.success ? r.flag : r.error);
});
$('next').addEventListener('click', e => { e.preventDefault(); load(); });
load();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "OddPixel/1.0"

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
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/challenge":
            token, png = make_challenge()
            rng = random.SystemRandom()
            self.send_json(200, {"token": token, "crew_id": rng.randint(1000, 9999), "slice": rng.randint(1, 240),
                                 "width": WIDTH, "height": HEIGHT, "time_limit": TIME_LIMIT,
                                 "image": base64.b64encode(png).decode()})
        elif path == "/static/chest-scan.png":
            with open(os.path.join(os.path.dirname(__file__), "static", "chest-scan.png"), "rb") as image:
                self.send(200, image.read(), "image/png")
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
        if self.path.split("?", 1)[0] != "/api/submit":
            return self.send_json(404, {"error": "not found"})
        try:
            f = self.read_json()
            token, x, y = str(f.get("token", "")), int(f["x"]), int(f["y"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "send JSON {token, x, y}"})
        ok, msg = check_answer(token, x, y)
        self.send_json(200 if ok else 403, {"success": ok, "flag" if ok else "error": msg})

def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"CT-7 (Odd Pixel) listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
