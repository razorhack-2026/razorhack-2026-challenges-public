#!/usr/bin/env python3
"""Reference solve for Odd Pixel. Usage: python3 solve.py [http://host:port]

Uses the JSON API the scanner page calls (visible in devtools). Standard library only: decodes the PNG by hand and finds the pixel that differs
from the majority colour.
"""
import base64
import json
import struct
import sys
import time
import urllib.request
import zlib
from collections import Counter

URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def decode_png_rgb(png):
    pos, idat, w, h = 8, b"", None, None
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos:pos + 8])
        data = png[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", data[:10])
            assert depth == 8 and ctype == 2, "expected 8-bit RGB"
        elif kind == b"IDAT":
            idat += data
        pos += 12 + length
    raw, stride, rows, prev = zlib.decompress(idat), w * 3, [], bytearray(w * 3)
    for y in range(h):
        ftype, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):  # undo PNG filters (server uses 0, but be general)
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if ftype == 1: line[i] = (line[i] + a) & 255
            elif ftype == 2: line[i] = (line[i] + b) & 255
            elif ftype == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif ftype == 4:
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line)); prev = line
    return w, h, rows


def main():
    t0 = time.time()
    chal = json.load(urllib.request.urlopen(f"{URL}/api/challenge"))
    w, h, rows = decode_png_rgb(base64.b64decode(chal["image"]))
    common = Counter(rows).most_common(1)[0][0]
    y = next(i for i, r in enumerate(rows) if r != common)
    x = next(i for i in range(w) if rows[y][3 * i:3 * i + 3] != common[3 * i:3 * i + 3])
    print(f"odd voxel at ({x}, {y}) found in {time.time() - t0:.3f}s")
    req = urllib.request.Request(f"{URL}/api/submit", method="POST",
                                 data=json.dumps({"token": chal["token"], "x": x, "y": y}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        print(json.load(urllib.request.urlopen(req))["flag"])
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode()); sys.exit(1)

if __name__ == "__main__":
    main()
