#!/usr/bin/env python3
"""FC-200 Field Diagnostic utility (competitor-facing program)."""
import random

_ROT = 3
_TARGET = b"\x9b\xb3\x1b\x69\xb9\xb9\x99\x89\x69\xab\x73\x63\x7b\x1b\x5b"
_SCRAMBLED = b"\x63\x63\x9b\x1b\x0b\x23\x4b\x2b\x73\x63\x01\x9b\x2b\x0b\x0b\x69\x63\x3b\x93\x4b\x91\x79\x4b\x1a\xfa\xa3\x01\x2b\x01\x01\x93\x1b\x2b\x23\x7b\x32\x2b\x63\xab\xfa\x0b\x63\xcb\x7b\x13\xeb\x9b\x3b\xdb\x93\x4b\x1b\x5b\x23\x3b\xa3\x33\xfa\xfa\x81\x81\x01\x2b\x23"


def _rotl(b, n):
    return ((b << n) | (b >> (8 - n))) & 0xFF


def _rotr(b, n):
    return ((b >> n) | (b << (8 - n))) & 0xFF


def _roll(data):
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = _rotl(data[i], _ROT)
    return bytes(out)


def _unlock(code):
    n = len(_SCRAMBLED)
    order = list(range(n))
    random.Random(int.from_bytes(code, "big")).shuffle(order)
    out = bytearray(n)
    for i in range(n):
        out[order[i]] = _rotr(_SCRAMBLED[i], _ROT)
    return bytes(out).decode()


def main():
    print("FC-200 Field Diagnostic  v3.1")
    print("panel: NOMINAL   bus: NOMINAL   cal: LOCKED")
    code = input("enter service code for full calibration readout: ").strip().encode()
    if len(code) == len(_TARGET) and _roll(code) == _TARGET:
        print("-- full calibration readout --")
        print(_unlock(code))
    else:
        print("service code rejected - readout stays locked")


if __name__ == "__main__":
    main()
