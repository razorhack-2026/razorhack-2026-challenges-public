#!/usr/bin/env python3
"""
Reference solve for "Nothing to Report".

Only the BODY paragraph(s) encode anything -- the two header lines (title +
recovered-from note) and the blank line separating them from the body are
not part of the encoding. See solution.md for how a competitor is expected
to figure that out from the document's own visual structure.

For each body word: strip leading/trailing punctuation, look at the first
alphabetic character. Vowel = 1, consonant = 0. Bits in reading order, 8 per
byte, MSB-first, decoded as ASCII.

Usage:
    python solve.py ../dist/shift_log.txt
"""
import string
import sys

VOWELS = set("aeiouAEIOU")


def extract_body(text: str) -> str:
    # Body is everything after the first blank line.
    parts = text.split("\n\n", 1)
    return parts[1] if len(parts) > 1 else parts[0]


def bit_for_word(word: str) -> int:
    stripped = word.strip(string.punctuation)
    return 1 if stripped and stripped[0] in VOWELS else 0


def decode(path: str) -> str:
    with open(path) as f:
        text = f.read()

    body = extract_body(text)
    words = body.split()
    bits = [bit_for_word(w) for w in words]

    # Trim to a whole number of bytes, MSB-first.
    nbytes = len(bits) // 8
    out = bytearray()
    for i in range(nbytes):
        byte = 0
        for b in bits[i * 8:(i + 1) * 8]:
            byte = (byte << 1) | b
        out.append(byte)

    return out.decode("ascii", errors="replace")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../dist/shift_log.txt"
    flag = decode(path)
    print(f"[+] Flag: {flag}")


if __name__ == "__main__":
    main()
