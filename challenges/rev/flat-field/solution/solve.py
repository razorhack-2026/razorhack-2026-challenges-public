"""Flat Field reference solver — recovers the calibration mask from dist/ only.

Reimplements what lenscal does (recovered from the binary):
  seed  = FNV-1a over every pixel's RED byte, ^ (w<<16 | h), ^ 0x4C454E53
  rng   = xorshift32 (13, 17, 5)
  per mask bit: idx = rng() % (w*h), redrawn while idx already used;
                k = rng() & 3; blue low 2 bits = k (bit 0) or k^3 (bit 1)

    python solve.py ../dist/condor_cal.png [mask.png]
"""
import struct
import sys

import numpy as np
from PIL import Image

M32 = 0xFFFFFFFF

px = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
h, w, _ = px.shape
npix = w * h
red = px[:, :, 0].ravel()
blue = px[:, :, 2].ravel()

# FNV-1a over the red channel (red is never modified, so the seed survives)
hsh = 0x811C9DC5
for r in red.tolist():
    hsh = ((hsh ^ r) * 0x01000193) & M32
state = hsh ^ ((w << 16) | h) ^ 0x4C454E53 or 1


def rng():
    global state
    x = state
    x ^= (x << 13) & M32
    x ^= x >> 17
    x ^= (x << 5) & M32
    state = x
    return x


used = bytearray(npix)


def read_bits(n):
    out = []
    for _ in range(n):
        while True:
            idx = rng() % npix
            if not used[idx]:
                break
        used[idx] = 1
        k = rng() & 3
        d = (int(blue[idx]) & 3) ^ k
        assert d in (0, 3), "desync — seed/PRNG/order is wrong"
        out.append(1 if d == 3 else 0)
    return out


def to_bytes(bits):
    return bytes(sum(b << (7 - j) for j, b in enumerate(bits[i:i + 8]))
                 for i in range(0, len(bits), 8))


# header first: it tells us how many more bits to pull
hdr = to_bytes(read_bits(64))
magic, mw, mh = hdr[:4], *struct.unpack("<HH", hdr[4:8])
assert magic == b"CAL1", magic
body_bits = read_bits(((mw * mh + 7) // 8) * 8)

mask = np.array(body_bits[:mw * mh], dtype=np.uint8).reshape(mh, mw)
out = sys.argv[2] if len(sys.argv) > 2 else "mask.png"
Image.fromarray((1 - mask) * 255).resize((mw * 3, mh * 3), Image.NEAREST).save(out)
print(f"CAL1 mask {mw}x{mh} -> {out}  (read the flag off the image)")
