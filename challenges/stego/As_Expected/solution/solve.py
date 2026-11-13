#!/usr/bin/env python3
"""Reference solve for As Expected.

dist/output.txt is one giant unbroken blob of text. Somewhere in it,
oversized whitespace gaps have been inserted so that wrapping the blob at
the WRONG chars-per-line looks like noise, but wrapping it at the correct
width lines the gaps up into a fixed 5x7 font, letter by letter, spelling
out the flag. No width is stated anywhere in the file.

dist/checksum.txt gives a sha256 of the first BLOCK_SIZE characters of
the raw dump, but never says what BLOCK_SIZE is. That's the oracle: brute
force candidate widths, hash each one's prefix, and the one that matches
is the real chars-per-line.

Once the width is known, a competitor doesn't need to write any kind of
renderer -- `fold -w <width> dist/output.txt` (or any editor set to wrap
at that column) already reveals the picture, since the width is the only
unknown. This script additionally decodes it automatically (for an exact,
scriptable flag check) using the same font table the challenge was built
from -- see src/letter_gap_scaffold.py for the generator.
"""
import hashlib
import re

GAP_RUN = re.compile(r" {10,}")
GAP_LEN = 12
LETTER_WIDTH = 5
LETTER_HEIGHT = 7
LINES_PER_CHAR = 15  # 7 rows x 2 (duplicated) + 1 separator line

FONT_BITMAPS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00010", "00100", "01000", "10000", "10000", "11111"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "a": ["00000", "01110", "00001", "01111", "10001", "10001", "01111"],
    "b": ["10000", "10000", "11110", "10001", "10001", "10001", "11110"],
    "c": ["00000", "01111", "10000", "10000", "10000", "10000", "01111"],
    "d": ["00001", "00001", "01111", "10001", "10001", "10001", "01111"],
    "e": ["00000", "01110", "10001", "11111", "10000", "10000", "01111"],
    "f": ["00110", "01001", "01000", "11100", "01000", "01000", "01000"],
    "g": ["00000", "01111", "10001", "10001", "01111", "00001", "01110"],
    "h": ["10000", "10000", "11110", "10001", "10001", "10001", "10001"],
    "i": ["00100", "00000", "01100", "00100", "00100", "00100", "01110"],
    "j": ["00010", "00000", "00110", "00010", "00010", "10010", "01100"],
    "k": ["10000", "10000", "10010", "10100", "11000", "10100", "10010"],
    "l": ["01100", "00100", "00100", "00100", "00100", "00100", "01110"],
    "m": ["00000", "11010", "10101", "10101", "10101", "10001", "10001"],
    "n": ["00000", "10110", "11001", "10001", "10001", "10001", "10001"],
    "o": ["00000", "01110", "10001", "10001", "10001", "10001", "01110"],
    "p": ["00000", "11110", "10001", "10001", "11110", "10000", "10000"],
    "q": ["00000", "01111", "10001", "10001", "01111", "00001", "00001"],
    "r": ["00000", "10110", "11001", "10000", "10000", "10000", "10000"],
    "s": ["00000", "01111", "10000", "01110", "00001", "10001", "01110"],
    "t": ["00100", "01111", "00100", "00100", "00100", "00100", "00011"],
    "u": ["00000", "10001", "10001", "10001", "10001", "10001", "01111"],
    "v": ["00000", "10001", "10001", "10001", "10001", "01010", "00100"],
    "w": ["00000", "10001", "10001", "10101", "10101", "10101", "01010"],
    "x": ["00000", "10001", "01010", "00100", "01010", "10001", "10001"],
    "y": ["00000", "10001", "10001", "10001", "01111", "00001", "01110"],
    "z": ["00000", "11111", "00010", "00100", "01000", "11111", "00000"],
    "{": ["00011", "00100", "00100", "01000", "00100", "00100", "00011"],
    "}": ["11000", "00100", "00100", "00010", "00100", "00100", "11000"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
}

REVERSE_FONT = {tuple(v): k for k, v in FONT_BITMAPS.items()}


def find_width(text, target_hash, lo=1, hi=10000):
    """Brute-force the block size the checksum was computed over: hash
    each candidate prefix length and compare against the given sha256."""
    for w in range(lo, hi + 1):
        if hashlib.sha256(text[:w].encode()).hexdigest() == target_hash:
            return w
    return None


def row_bits(line, slot_cols, tol=2):
    """1 if a real (>=GAP_LEN) gap run overlaps this slot's column, else 0.
    Checking for overlap in a small +/-tol window -- not an exact
    start-offset match -- makes this robust to a slot's gap run getting
    extended by a naturally-occurring space immediately before/after it
    in the filler text. tol must stay well under GAP_LEN so neighboring
    slots (GAP_LEN apart) can't bleed into each other."""
    bits = ""
    for c in slot_cols:
        window = line[max(0, c - tol):c + GAP_LEN + tol]
        bits += "1" if GAP_RUN.search(window) else "0"
    return bits


def decode(text, width):
    start = width // 4
    slot_cols = [start + GAP_LEN * i for i in range(LETTER_WIDTH)]

    lines = [text[i:i + width] for i in range(0, len(text), width)]
    bit_rows = [row_bits(line, slot_cols) for line in lines]

    active = [i for i, b in enumerate(bit_rows) if b != "0" * LETTER_WIDTH]
    if not active:
        raise SystemExit("no picture signal found at the detected width")
    start_line = active[0]

    flag_chars = []
    i = start_line
    while i + LETTER_HEIGHT * 2 <= len(bit_rows):
        rows = tuple(bit_rows[i + j] for j in range(0, LETTER_HEIGHT * 2, 2))
        if rows not in REVERSE_FONT:
            break
        char = REVERSE_FONT[rows]
        flag_chars.append(char)
        if char == "}":
            break
        i += LINES_PER_CHAR

    return "".join(flag_chars)


def main():
    with open("dist/output.txt", encoding="utf-8") as f:
        text = f.read().replace("\n", "")
    with open("dist/checksum.txt", encoding="utf-8") as f:
        target_hash = next(line for line in f if line.startswith("checksum")).split(":")[1].strip()

    width = find_width(text, target_hash)
    if width is None:
        raise SystemExit("no width in range matched the checksum")
    flag = decode(text, width)

    print(f"detected width : {width}")
    print(f"flag           : {flag}")


if __name__ == "__main__":
    main()
