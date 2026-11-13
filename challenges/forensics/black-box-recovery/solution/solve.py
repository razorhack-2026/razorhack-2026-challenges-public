#!/usr/bin/env python3
"""
Black Box Recovery - reference solver (stdlib only).

The deleted abort_log.txt was NTFS-compressed and its run list is zeroed, so
no tool will follow the MFT record to its clusters. The compressed data still
sits in unallocated clusters. Every compression unit starts on a cluster
boundary with an LZNT1 chunk header (signature bits 0x3000), so: walk the
image cluster by cluster, decompress any run of valid chunks, and keep the
output that reads as the recorder's log.

usage: solve.py <blackbox.img> [cluster_size]
"""
import re
import sys


def lznt1_chunk(data):
    """Decompress one LZNT1 chunk body (header already stripped)."""
    out = bytearray()
    i = 0
    while i < len(data):
        tags = data[i]
        i += 1
        for bit in range(8):
            if i >= len(data):
                break
            if not (tags >> bit) & 1:
                out.append(data[i])
                i += 1
                continue
            if i + 2 > len(data):
                raise ValueError("truncated back-reference")
            tok = int.from_bytes(data[i:i + 2], "little")
            i += 2
            # The offset/length split moves as the chunk output grows.
            pos = len(out) - 1
            if pos < 0:
                raise ValueError("back-reference before any output")
            len_mask, off_shift = 0xFFF, 12
            while pos >= 0x10:
                len_mask >>= 1
                off_shift -= 1
                pos >>= 1
            off = (tok >> off_shift) + 1
            n = (tok & len_mask) + 3
            if off > len(out):
                raise ValueError("back-reference out of range")
            for _ in range(n):
                out.append(out[-off])
    return bytes(out)


def lznt1_stream(buf, start):
    """Decompress consecutive chunks from buf[start:] until a zero header."""
    out = bytearray()
    i = start
    while i + 2 <= len(buf):
        hdr = int.from_bytes(buf[i:i + 2], "little")
        if hdr == 0:
            break
        if (hdr >> 12) & 0x7 != 0x3:
            raise ValueError("bad chunk signature")
        size = (hdr & 0xFFF) + 1
        body = buf[i + 2:i + 2 + size]
        chunk = lznt1_chunk(body) if hdr & 0x8000 else body
        if len(chunk) > 4096:
            raise ValueError("oversized chunk")
        out += chunk
        i += 2 + size
    return bytes(out)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} <image> [cluster_size]")
    img = open(sys.argv[1], "rb").read()
    cluster = int(sys.argv[2]) if len(sys.argv) > 2 else 4096

    found = set()
    for off in range(0, len(img), cluster):
        hdr = int.from_bytes(img[off:off + 2], "little")
        if not hdr & 0x8000 or (hdr >> 12) & 0x7 != 0x3:
            continue
        try:
            text = lznt1_stream(img, off)
        except (ValueError, IndexError):
            continue
        if b"ABORT LOG" not in text:
            continue
        print(f"[+] LZNT1 abort log at image offset {off} "
              f"(cluster {off // cluster}), {len(text)} bytes decompressed")
        for line in text.splitlines():
            if b"override" in line:
                print("    " + line.decode(errors="replace"))
        found.update(re.findall(rb"flag\{[^}]*\}", text))

    if not found:
        raise SystemExit("[-] no compressed abort log recovered")
    for flag in sorted(found):
        print(flag.decode())


if __name__ == "__main__":
    main()
