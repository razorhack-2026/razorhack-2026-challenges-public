#!/usr/bin/env python3
"""Mirror, Mirror (medbay, CT-7): find the lesion in a 3D brain CT volume.

Every challenge is a fresh 512x512x512 brain CT, generated on demand one
slice at a time. Somewhere in the brain tissue is a small sphere whose
density is only slightly off, well below the per-voxel scanner noise, so
no single voxel or slice gives it away. Bright calcifications are normal
and act as red herrings. Scroll the layers with the slider, click the
lesion before the exposure window closes.

Needs numpy. Each challenge gets a single-use token; the time limit is
enforced server-side.
"""
import hashlib
import json
import os
import secrets
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np

FLAG = os.environ["FLAG"]
SIZE = int(os.environ.get("SIZE", "512"))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", "30"))
NOISE = float(os.environ.get("NOISE", "20"))         # per-voxel Gaussian noise (grey levels)
CONTRAST = float(os.environ.get("CONTRAST", "14"))   # lesion density offset, still below voxel noise
TOLERANCE = float(os.environ.get("TOLERANCE", "2"))  # extra voxels allowed outside the lesion
MAX_PENDING = 2000
MAX_BODY_BYTES = 4096

TISSUE, CSF, BONE, CALC = 100, 48, 220, 235

_pending = {}  # token -> Volume
_lock = threading.Lock()


class Volume:
    """A procedural brain phantom. All geometry is in voxel units for SIZE."""

    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.seed = seed
        self.issued = time.monotonic()
        n = SIZE
        s = n / 512 * rng.uniform(0.95, 1.05)          # patient size
        c = n / 2 + rng.uniform(-12, 12, 3) * n / 512  # patient position (x, y, z)
        self.scale = s
        self.center = tuple(c)
        self.radii = (155 * s, 190 * s, 170 * s)

        self.calcs = []  # (x, y, z, r): normal, high-contrast red herrings
        while len(self.calcs) < 14:
            p = rng.uniform(0, n, 3)
            if self.label(*p) == TISSUE:
                self.calcs.append((*p, rng.uniform(2, 4) * n / 512))

        # the lesion: deep in plain soft tissue, nowhere near an edge
        self.r = 9 * n / 512
        margin = 20 * n / 512
        starting_z = n // 2 + 0.5  # Voxel-center plane of the first displayed slice.
        offsets = np.array(np.meshgrid(*[[-margin, 0, margin]] * 3)).reshape(3, -1).T
        while True:
            p = rng.uniform(0, n, 3)
            if abs(p[2] - starting_z) <= self.r + max(0, TOLERANCE):
                continue
            if all(self.label(*(p + o)) == TISSUE for o in offsets) and \
                    all(np.linalg.norm(p - q[:3]) > margin for q in self.calcs):
                break
        self.lesion = p
        self.delta = CONTRAST * rng.choice([-1, 1])

    def label(self, x, y, z):
        """Density of the noiseless phantom at one point (used for placement)."""
        img = self.render(np.array([[x]]), np.array([[y]]), z, with_lesion=False)
        return int(img[0, 0])

    def render(self, X, Y, z, with_lesion=True):
        cx, cy, cz = self.center
        rx, ry, rz = self.radii
        s = self.scale
        img = np.zeros(X.shape, np.float32)
        brain = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1
        skull = ((X - cx) / (rx + 8 * s) ) ** 2 + ((Y - cy) / (ry + 8 * s)) ** 2 + \
                ((z - cz) / (rz + 8 * s)) ** 2 <= 1
        img[brain] = TISSUE
        img[skull & ~brain] = BONE

        # Central fissure and paired ventricles provide normal low-density anatomy.
        fissure = brain & (np.abs(X - cx) < 2 * s) & (abs(z - cz) < 0.8 * rz)
        img[fissure] = CSF
        for side in (-1, 1):
            ventricle = ((X - (cx + side * 32 * s)) / (18 * s)) ** 2 + \
                        ((Y - (cy - 10 * s)) / (34 * s)) ** 2 + \
                        ((z - (cz + 5 * s)) / (48 * s)) ** 2 <= 1
            img[ventricle & brain] = CSF
        for cx, cy, cz, r in self.calcs:
            if abs(z - cz) <= r:
                img[(X - cx) ** 2 + (Y - cy) ** 2 + (z - cz) ** 2 <= r * r] = CALC
        if with_lesion:
            lx, ly, lz = self.lesion
            if abs(z - lz) <= self.r:
                img[(X - lx) ** 2 + (Y - ly) ** 2 + (z - lz) ** 2 <= self.r ** 2] += self.delta
        return img

    def slice(self, z):
        Y, X = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) + 0.5
        img = self.render(X, Y, z + 0.5)
        noise_seed = int.from_bytes(hashlib.sha256(f"{self.seed}:{z}".encode()).digest()[:8], "big")
        img += np.random.default_rng(noise_seed).normal(0, NOISE, img.shape).astype(np.float32)
        return np.clip(np.rint(img), 0, 255).astype(np.uint8)

    def hit(self, x, y, z):
        d = np.linalg.norm(np.array([x, y, z]) + 0.5 - self.lesion)
        return d <= self.r + TOLERANCE


def encode_png(gray):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    h, w = gray.shape
    raw = np.hstack([np.zeros((h, 1), np.uint8), gray]).tobytes()  # filter type 0 on every row
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)  # 8-bit greyscale
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))


def new_challenge():
    token = secrets.token_urlsafe(16)
    vol = Volume(secrets.randbits(64))
    now = time.monotonic()
    with _lock:
        for t in [t for t, v in _pending.items() if now - v.issued > TIME_LIMIT + 5]:
            del _pending[t]
        if len(_pending) >= MAX_PENDING:
            _pending.pop(next(iter(_pending)))
        _pending[token] = vol
    return token


def get_live(token):
    with _lock:
        vol = _pending.get(token)
    if vol is None or time.monotonic() - vol.issued > TIME_LIMIT:
        return None
    return vol


def check_answer(token, x, y, z):
    with _lock:
        vol = _pending.pop(token, None)  # single use, right or wrong
    if vol is None:
        return False, "Unknown or already used token. Start a new scan."
    if time.monotonic() - vol.issued > TIME_LIMIT:
        return False, f"Exposure window closed. You have {TIME_LIMIT:g} seconds."
    if not vol.hit(x, y, z):
        return False, "Healthy tissue there. Wrong spot."
    return True, FLAG


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>CT-7 | Medbay</title>
<style>
 body{font-family:ui-monospace,Menlo,Consolas,monospace;background:#05100f;color:#7fe0c8;text-align:center;padding:1.5em}
 h1{letter-spacing:.2em;font-weight:400;margin:.2em} .dim{color:#3f8f7f} .warn{color:#ffb347}
 .panel{display:inline-block;border:1px solid #1f5f55;padding:1.2em;background:#071a18;max-width:100%;box-sizing:border-box}
 .workbench{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:1.2em;align-items:start}
 .task{min-width:0;text-align:center}.reference{width:260px;text-align:left;padding:.8em;border:1px solid #17473f;background:#061512;box-sizing:border-box}
 .reference h2{font-weight:400;font-size:1em;letter-spacing:.12em;margin:.5em 0}
 .scan-window{position:relative;overflow:hidden;background:#000;border:1px solid #2f8f7f;aspect-ratio:1.28}
 .scan-window img{position:absolute;width:172%;max-width:none;height:auto;left:-36%;top:50%;transform:translateY(-50%);border:0;margin:0}
 #img{border:1px solid #2f8f7f;cursor:crosshair;image-rendering:pixelated;display:block;margin:.8em auto;background:#000;max-width:100%}
 input[type=range]{width:100%;accent-color:#7fe0c8} #t{font-size:1.8em;font-variant-numeric:tabular-nums} a{color:#9ff} #res{min-height:1.4em}
 @media(max-width:1050px){.workbench{grid-template-columns:1fr}.reference{width:100%;max-width:512px;margin:0 auto}}
</style></head><body>
<div class="dim">MEDBAY // AUTODOC: <span class="warn">LESION BELOW DETECTION THRESHOLD, MANUAL READ</span></div>
<h1>CT-7 NEURO TOMOGRAPH</h1>
<div class="panel">
<div class="workbench"><section class="task">
<div id="hdr">ACQUIRING VOLUME...</div>
<p>CT-7 has flagged an anomaly in the brain tissue.<br>
Calcifications are normal. Scroll the layers and mark the lesion before the dose limit closes the exposure window.</p>
<div>EXPOSURE WINDOW <span id="t" class="warn">-</span> s</div>
<img id="img" alt="CT-7 brain scan layer">
<input type="range" id="z" min="0" value="0">
<div>LAYER <span id="zl">0</span></div>
<div id="res"></div>
<div class="dim">[ <a href="#" id="next">new scan</a> ]</div>
</section><aside class="reference">
<div class="dim">PATIENT FILE // REFERENCE</div><h2>BRAIN SCAN</h2>
<div class="scan-window"><img src="/static/brain-scan.png" alt="Brain scan reference image"></div>
<p class="dim">Reference imaging from the neuro-med intake file.</p>
</aside></div>
</div>
<script>
const $ = id => document.getElementById(id);
let token = null, raf = 0, pending = 0;
function show() {
  const z = +$('z').value; $('zl').textContent = z;
  if (token) $('img').src = `/api/slice?token=${token}&z=${z}`;
}
async function load() {
  cancelAnimationFrame(raf); $('res').textContent = ''; $('img').style.opacity = 1;
  const c = await (await fetch('/api/challenge')).json();
  token = c.token;
  $('hdr').textContent = `CREW ${c.crew_id} · ${c.size}³ VOXELS · DENSITY MAP`;
  $('img').width = c.size; $('img').height = c.size;
  $('z').max = c.size - 1; $('z').value = c.size >> 1; show();
  const start = performance.now();
  const tick = () => {
    const r = Math.max(0, c.time_limit - (performance.now() - start) / 1000);
    $('t').textContent = r.toFixed(1);
    if (r > 0) raf = requestAnimationFrame(tick); else $('img').style.opacity = .15;
  };
  tick();
}
$('z').addEventListener('input', show);
$('img').addEventListener('click', async e => {
  if (!token) return;
  const img = e.currentTarget, b = img.getBoundingClientRect();
  const k = img.naturalWidth / img.clientWidth;
  const x = Math.floor((e.clientX - b.left - img.clientLeft) * k), y = Math.floor((e.clientY - b.top - img.clientTop) * k);
  const t = token; token = null; cancelAnimationFrame(raf);
  const r = await (await fetch('/api/submit', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                               body: JSON.stringify({token: t, x, y, z: +$('z').value})})).json();
  $('res').innerHTML = r.success ? '<b>LESION CONFIRMED</b> ' : '<b class="warn">READ REJECTED</b> ';
  $('res').append(r.success ? r.flag : r.error);
});
$('next').addEventListener('click', e => { e.preventDefault(); load(); });
load();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "MirrorMirror/1.0"
    protocol_version = "HTTP/1.1"  # keep-alive, so scripts can pull 512 layers quickly

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
        elif url.path == "/api/challenge":
            token = new_challenge()
            self.send_json(200, {"token": token, "crew_id": secrets.randbelow(9000) + 1000,
                                 "size": SIZE, "time_limit": TIME_LIMIT})
        elif url.path == "/api/slice":
            q = parse_qs(url.query)
            vol = get_live(q.get("token", [""])[0])
            if vol is None:
                return self.send_json(403, {"error": "Unknown token or exposure window closed."})
            try:
                z = int(q.get("z", ["x"])[0])
                assert 0 <= z < SIZE
            except (ValueError, AssertionError):
                return self.send_json(400, {"error": f"z must be 0..{SIZE - 1}"})
            self.send(200, encode_png(vol.slice(z)), "image/png")
        elif url.path == "/static/brain-scan.png":
            with open(os.path.join(os.path.dirname(__file__), "static", "brain-scan.png"), "rb") as image:
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
            token, x, y, z = str(f.get("token", "")), int(f["x"]), int(f["y"]), int(f["z"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "send JSON {token, x, y, z}"})
        ok, msg = check_answer(token, x, y, z)
        self.send_json(200 if ok else 403, {"success": ok, "flag" if ok else "error": msg})


def main():
    port = int(os.environ.get("PORT", "8000"))
    print(f"CT-7 (Mirror, Mirror) listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
