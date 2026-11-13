"""Render the flag as a 1-bit bitmap and write it as a CAL1 calibration mask.

CAL1 format (little-endian):
    0  4  magic  b"CAL1"
    4  2  width  (u16)
    6  2  height (u16)
    8  .. width*height bits, row-major, MSB-first, 1 = ink, final byte zero-padded

    python make_payload.py mask.cal [mask_preview.png]
"""
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

FLAG = "flag{the_mask_was_the_message}"

font = ImageFont.load_default(size=28)
left, top, right, bottom = font.getbbox(FLAG)
pad = 6
w, h = right - left + 2 * pad, bottom - top + 2 * pad

img = Image.new("1", (w, h), 0)
ImageDraw.Draw(img).text((pad - left, pad - top), FLAG, fill=1, font=font)

bits = [1 if img.getpixel((x, y)) else 0 for y in range(h) for x in range(w)]
bits += [0] * (-len(bits) % 8)
packed = bytes(
    sum(b << (7 - j) for j, b in enumerate(bits[i:i + 8]))
    for i in range(0, len(bits), 8)
)

with open(sys.argv[1], "wb") as f:
    f.write(b"CAL1" + struct.pack("<HH", w, h) + packed)
if len(sys.argv) > 2:
    img.save(sys.argv[2])
print(f"mask {w}x{h}, {8 + len(packed)} bytes")
