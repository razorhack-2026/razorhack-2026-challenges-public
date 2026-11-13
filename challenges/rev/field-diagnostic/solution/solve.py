#!/usr/bin/env python3
"""
Field Diagnostic — reference solver (GM-only).

Reads ONLY the competitor handout (dist/diagnostic.pyc). Imports nothing from
the build script and hardcodes no answer. Recovers the service code and flag
purely from the two byte constants embedded in the bytecode, the way a
competitor would after decompiling it.

Intended competitor path:
  1. Recognize dist/diagnostic.pyc as Python 3.8 bytecode; decompile it
     (uncompyle6 / decompyle3 / pycdc).
  2. Read the gate: each code byte is left-rotated by _ROT bits to equal
     _TARGET, so the service code is _TARGET right-rotated by _ROT.
  3. The full readout is _SCRAMBLED un-shuffled by the permutation
     random.Random(int.from_bytes(code,"big")).shuffle(order) and then each
     byte right-rotated by _ROT -> flag. (Or just run the tool under Python 3.8
     and type the recovered code.)

Marshal is version-specific and random.shuffle must match the build, so run
this under Python 3.8:
    uv run --python 3.8 python solve.py dist/diagnostic.pyc
"""
import marshal
import random
import re
import sys


def load_byte_consts(path):
    with open(path, "rb") as f:
        f.read(16)  # 3.7+ .pyc header
        code = marshal.load(f)
    found = []

    def walk(c):
        for k in c.co_consts:
            if isinstance(k, bytes):
                found.append(k)
            elif hasattr(k, "co_consts"):
                walk(k)

    walk(code)
    return found


def rotr(b, n):
    return ((b >> n) | (b << (8 - n))) & 0xFF


def unscramble(scrambled, code, rot):
    n = len(scrambled)
    order = list(range(n))
    random.Random(int.from_bytes(code, "big")).shuffle(order)
    out = bytearray(n)
    for i in range(n):
        out[order[i]] = rotr(scrambled[i], rot)   # un-permute and un-rotate
    return bytes(out)


def main(path):
    consts = sorted(load_byte_consts(path), key=len)
    if len(consts) < 2:
        print("expected two byte constants", file=sys.stderr)
        return 1
    target, scrambled = consts[0], consts[-1]   # code-length vs readout-length

    for rot in range(1, 8):                     # don't assume _ROT; try them
        code = bytes(rotr(b, rot) for b in target)
        if not all(32 <= c < 127 for c in code):
            continue
        try:
            text = unscramble(scrambled, code, rot).decode()
        except UnicodeDecodeError:
            continue
        m = re.search(r"flag\{[^}]+\}", text)
        if m:
            print("service code:", code.decode())
            print("readout:", text)
            print("FLAG:", m.group(0))
            return 0
    print("no flag recovered", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "../dist/diagnostic.pyc"))
