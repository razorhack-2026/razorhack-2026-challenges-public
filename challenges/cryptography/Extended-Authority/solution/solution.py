#!/usr/bin/env python3
"""
Solve script - Extended Authority: Directive Forgery (SHA-256 length extension).

Self-contained: the SHA-256 length extension is implemented below in pure Python
so the script has no third-party dependency (the classic `hashpumpy` binding fails
to build / import on modern CPython). Players may instead use `hashpumpy` or the
`hash_extender` CLI - see solution.md.

Usage:
    python3 solution.py http://localhost:8888
"""
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APPEND = b"|order=forged"
MAX_SECRET_LEN = 64
PACE = 0.6  # seconds between /verify calls; gateway throttles to 2 req/s

# ── Pure-Python SHA-256 with a resumable state (for length extension). ────────
_K = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1,
    0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
    0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174, 0xE49B69C1, 0xEFBE4786,
    0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147,
    0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
    0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85, 0xA2BFE8A1, 0xA81A664B,
    0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A,
    0x5B9CCA4F, 0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
]
_MASK = 0xFFFFFFFF

def _rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & _MASK

def _compress(h, block):
    w = list(struct.unpack(">16L", block))
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & _MASK)
    a, b, c, d, e, f, g, hh = h
    for i in range(64):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (hh + S1 + ch + _K[i] + w[i]) & _MASK
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & _MASK
        hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & _MASK, c, b, a, (t1 + t2) & _MASK
    return [(x + y) & _MASK for x, y in zip(h, (a, b, c, d, e, f, g, hh))]

def _md_pad(msg_len):
    """The padding SHA-256 appends to a message of `msg_len` bytes."""
    pad = b"\x80" + b"\x00" * ((56 - (msg_len + 1) % 64) % 64)
    return pad + struct.pack(">Q", msg_len * 8)

def length_extend(orig_checksum_hex, orig_msg, append, key_len):
    """Return (forged_message, forged_checksum_hex) for SHA256(secret || orig_msg).

    `key_len` is the guessed length of the unknown secret prefix.
    """
    glue = _md_pad(key_len + len(orig_msg))
    forged_msg = orig_msg + glue + append
    # Resume from the published digest; the hasher has already consumed
    # key_len + len(orig_msg) + len(glue) bytes (a whole number of 64-byte blocks).
    h = list(struct.unpack(">8L", bytes.fromhex(orig_checksum_hex)))
    already = key_len + len(orig_msg) + len(glue)
    tail = append + _md_pad(already + len(append))
    for i in range(0, len(tail), 64):
        h = _compress(h, tail[i:i + 64])
    return forged_msg, "".join(f"{x:08x}" for x in h)

DIRECTIVE_HEX = (
    "5250435f43454e54434f4d7c763d317c68756c6c3d4943415255537c7072693d"
    "726f7574696e657c6f726465723d44454c495645525f5041594c4f4144"
)

def _get_sample(base):
    """Hard-coded directive + the live checksum scraped off the homepage."""
    with urllib.request.urlopen(base.rstrip("/") + "/", timeout=20) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'"checksum":\s*"([0-9a-fA-F]{64})"', html)
    if not m:
        sys.exit("[!] could not find the checksum on the gateway homepage")
    return {"directive": DIRECTIVE_HEX, "checksum": m.group(1).lower()}

def _verify(base, directive_hex, checksum):
    data = urllib.parse.urlencode({"directive_hex": directive_hex, "checksum": checksum}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/verify", data=data)
    while True:
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:  # throttled - honor Retry-After and retry
                time.sleep(float(e.headers.get("Retry-After", "1")) + 0.2)
                continue
            return e.read().decode("utf-8", "replace")

def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} http://host:port")
    base = sys.argv[1]

    sample = _get_sample(base)
    directive = bytes.fromhex(sample["directive"])
    checksum = sample["checksum"]
    print(f"[*] sample directive = {directive!r}")
    print(f"[*] sample checksum  = {checksum}")
    print(f"[*] appending        = {APPEND!r}")
    print("[*] brute-forcing secret length")

    for klen in range(0, MAX_SECRET_LEN + 1):
        forged_msg, forged_checksum = length_extend(checksum, directive, APPEND, klen)
        resp = _verify(base, forged_msg.hex(), forged_checksum)
        m = re.search(r"flag\{[^}]+\}", resp)
        if m:
            print(f"[+] secret length  = {klen}")
            print(f"[+] directive_hex  = {forged_msg.hex()}")
            print(f"[+] checksum       = {forged_checksum}")
            print(f"[+] {m.group(0)}")
            return
        if "AUTHENTICATED" in resp:
            print(f"[!] authenticated at klen={klen} but no flag: {resp.strip()}")
        time.sleep(PACE)

    sys.exit("[!] no key length in range produced a valid forgery")


if __name__ == "__main__":
    main()
