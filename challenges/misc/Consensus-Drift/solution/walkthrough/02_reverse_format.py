#!/usr/bin/env python3
"""Step 2 -- Reverse the node-DB container format (no spec is shipped).

Discovers, from the raw bytes: the `CVND` magic, the 12-byte file header, and the
length-framed record structure `type:1 + length:3(LE) + payload`. The framing is proven by
walking it: a correct guess consumes exactly `rec_count` records and lands on EOF.

Run: python solution/walkthrough/02_reverse_format.py
"""
import os, struct, collections

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONVOY = os.path.join(ROOT, "dist", "convoy")


def hexdump(data, n=96):
    for i in range(0, n, 16):
        chunk = data[i:i+16]
        hexs = " ".join(f"{b:02x}" for b in chunk).ljust(47)
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{i:04x}  {hexs}  {asci}")


def main():
    data = open(os.path.join(CONVOY, "node-01.db"), "rb").read()

    print("=== hexdump of node-01.db (note ASCII 'CVND' magic at offset 0) ===")
    hexdump(data)

    print("\n=== diff the first 12 bytes of two files (byte 5 = node id) ===")
    a = open(os.path.join(CONVOY, "node-01.db"), "rb").read()[:12]
    b = open(os.path.join(CONVOY, "node-02.db"), "rb").read()[:12]
    print("node-01:", a.hex())
    print("node-02:", b.hex())

    print("\n=== prove the framing hypothesis: type:1 + length:3(LE) + payload ===")
    assert data[:4] == b"CVND"
    rec_count = struct.unpack("<I", data[8:12])[0]
    off, n, hist = 12, 0, collections.Counter()
    while off < len(data):
        rtype = data[off]
        length = int.from_bytes(data[off+1:off+4], "little")
        off += 4 + length
        hist[(rtype, length)] += 1
        n += 1
    print(f"declared rec_count={rec_count}  walked={n}  landed on EOF={off == len(data)}")
    for (rtype, length), count in sorted(hist.items()):
        print(f"  type {rtype}  payload_len {length}  x{count}")


if __name__ == "__main__":
    main()
