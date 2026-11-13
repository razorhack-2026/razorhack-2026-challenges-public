#!/usr/bin/env python3
"""Reference solve for the CT-7 lesion challenge.

Usage: python3 solve.py [http://host:8000]   (needs numpy)

1. Pull all layers in parallel and stack them into a volume.
2. Average 2x2x2 blocks, then a 5x5x5 box filter: noise drops ~30x,
   the lesion (a sphere ~18 voxels across) survives.
3. Keep only voxels deep inside plain soft tissue and away from the bright
   calcifications (both would otherwise win), and pick the one furthest
   from the typical tissue density.
"""
import json
import struct
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

import numpy as np

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return r.read()


def decode_png(data):
    """8-bit greyscale PNG with filter type 0 rows (what CT-7 sends)."""
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    rows = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, w + 1)
    assert not rows[:, 0].any(), "unexpected PNG row filter"
    return rows[:, 1:]


def box(v, k):
    """k-wide moving average along every axis (same shape, edges approximate)."""
    for ax in range(3):
        c = np.cumsum(v, axis=ax, dtype=np.float32)
        pad = [(0, 0)] * 3
        pad[ax] = (1, 0)
        c = np.pad(c, pad)
        n = v.shape[ax]
        lo = np.clip(np.arange(n) - k // 2, 0, n)
        hi = np.clip(np.arange(n) + k // 2 + 1, 0, n)
        v = (np.take(c, hi, axis=ax) - np.take(c, lo, axis=ax)) / (hi - lo).reshape(
            [-1 if a == ax else 1 for a in range(3)])
    return v


def locate(vol):
    n = vol.shape[0]
    d = vol.reshape(n // 2, 2, n // 2, 2, n // 2, 2).mean((1, 3, 5), dtype=np.float32)  # [z, y, x]
    s = box(d, 5)
    tissue = (s > 80) & (s < 120)
    near_bright = box((d > 180).astype(np.float32), 9) > 0  # calcifications are normal; stay clear
    near_low = box((d < 65).astype(np.float32), 9) > 0  # ventricles and CSF are normal; stay clear
    deep = tissue & ~near_bright & ~near_low
    for ax in range(3):
        for k in (2, 4, 6, 8):
            deep &= np.roll(tissue, k, ax) & np.roll(tissue, -k, ax)
    level = np.median(s[deep])
    score = np.where(deep, np.abs(s - level), 0)
    z, y, x = np.unravel_index(np.argmax(score), score.shape)
    return int(x * 2 + 1), int(y * 2 + 1), int(z * 2 + 1), float(score[z, y, x])


def main():
    t0 = time.time()
    c = json.loads(get("/api/challenge"))
    tok, n = c["token"], c["size"]
    with ThreadPoolExecutor(16) as ex:
        layers = list(ex.map(lambda z: decode_png(get(f"/api/slice?token={tok}&z={z}")), range(n)))
    t1 = time.time()
    x, y, z, score = locate(np.stack(layers))
    t2 = time.time()
    body = json.dumps({"token": tok, "x": x, "y": y, "z": z}).encode()
    req = urllib.request.Request(BASE + "/api/submit", body, {"Content-Type": "application/json"})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        res = json.loads(e.read())
    print(f"download {t1 - t0:.1f}s, analysis {t2 - t1:.1f}s, total {time.time() - t0:.1f}s "
          f"of {c['time_limit']:g}s; clicked ({x}, {y}, layer {z}), offset {score:.1f}")
    print(res)
    return 0 if res.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
