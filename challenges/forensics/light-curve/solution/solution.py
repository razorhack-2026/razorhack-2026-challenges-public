#!/usr/bin/env python3
"""
Reference solver for Light Curve (GM-only).

The scaled_value column is a decoy transit light curve. The flag is hidden
in the least-significant bit of each raw_value register, framed by a 16-bit
sync word (0xA5A5) and an 8-bit length prefix, in row order.
"""
import csv
import sys

SYNC_WORD = 0xA5A5


def bits_to_int(bits):
    n = 0
    for bit in bits:
        n = (n << 1) | bit
    return n


def main(path="light_curve.csv"):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    bits = [int(r["raw_value"]) & 1 for r in rows]

    sync = bits_to_int(bits[0:16])
    if sync != SYNC_WORD:
        print(f"Sync word mismatch: got 0x{sync:04X}, expected 0x{SYNC_WORD:04X}")
        sys.exit(1)

    length = bits_to_int(bits[16:24])
    payload_bits = bits[24:24 + 8 * length]
    if len(payload_bits) < 8 * length:
        print("File is truncated relative to the declared length.")
        sys.exit(1)

    chars = []
    for i in range(0, len(payload_bits), 8):
        chars.append(chr(bits_to_int(payload_bits[i:i + 8])))

    print("".join(chars))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "light_curve.csv")
