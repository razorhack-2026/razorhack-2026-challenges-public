#!/usr/bin/env python3
"""Organizer check: unwrap shield_phase.bin and print the flag."""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
BLOB = os.path.join(ROOT, "dist", "shield_phase.bin")
KEY = hashlib.md5(b"shield").digest()
VIGENERE_KEY = "MICROBOT"


def vigenere_decrypt(ct: str, key: str) -> str:
    out = []
    ki = 0
    for c in ct:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            k = ord(key[ki % len(key)].upper()) - ord("A")
            out.append(chr((ord(c) - base - k) % 26 + base))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


def main():
    ct = bytes.fromhex(open(BLOB, encoding="ascii").read().strip())
    proc = subprocess.run(
        ["openssl", "enc", "-d", "-aes-128-ecb", "-K", KEY.hex(), "-nosalt"],
        input=ct,
        capture_output=True,
        check=True,
    )
    layer1 = proc.stdout.decode("ascii")
    pt = vigenere_decrypt(layer1, VIGENERE_KEY)
    print(pt)
    if "flag{" not in pt:
        sys.exit("no flag in plaintext")


if __name__ == "__main__":
    main()
