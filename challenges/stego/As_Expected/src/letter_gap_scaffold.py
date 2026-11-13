#!/usr/bin/env python3
"""
Letter gap scaffold.

Edit FONT_BITMAPS below to tune any letter's shape. Each letter is 7 rows
(top to bottom, upright/normal reading orientation -- NOT sideways; pass
--sideways on the CLI to rotate at render time). Each row is a 5-character
string of '1' (gap/space -- the picture) and '0' (fill -- where real text
from your source file goes).

Bitmaps are the editable source of truth here, not run-length lists --
every row is automatically the right width just by being a 5-character
string, so there's no sum-the-numbers-correctly bug to make (that's
exactly what broke on the first version of this file). If you want to see
any letter in the "2 space, 2 filled, 2 space, 4 filled" run-length format
you described, run this file with --runs <LETTER> and it's computed for
you from the bitmap automatically.
"""
import argparse
import random
import re

# On-theme filler phrases, randomly strung together for the source text
# instead of one single repeated line -- varied enough word lengths that
# the gaps don't land on the same spot every cycle (which would show up
# as a visible repeating seam in the output).
THEMED_PHRASES = [
    "status nominal docking ring three holding steady on the long watch ",
    "relay station nominal all systems holding steady out past the ring ",
    "nothing to report nothing to report the watch continues as scheduled ",
]

# The correct chars-per-line to wrap at. No clue is stated anywhere in the
# file on purpose -- the competitor has to detect it (e.g. by scoring how
# well the inserted gaps line up into columns at each candidate width),
# not read it off a line of text.
LINE_LEN = 3823


def build_themed_source(repeats: int = 100000) -> str:
    return "".join(random.choices(THEMED_PHRASES, k=repeats))

LETTER_WIDTH = 5
LETTER_HEIGHT = 7

# ---------------------------------------------------------------------------
# EDIT THIS. '1' = gap (the picture). '0' = fill (real text goes here).
# ---------------------------------------------------------------------------
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

    # Lowercase -- distinct glyphs (shorter x-height, descenders on g/j/p/q/y),
    # not just aliases of the uppercase shapes. Less carefully proofed than the
    # uppercase set above; tune freely, the self-check only validates dimensions.
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

    # Flag syntax: flag{...} needs these three.
    "{": ["00011", "00100", "00100", "01000", "00100", "00100", "00011"],
    "}": ["11000", "00100", "00100", "00010", "00100", "00100", "11000"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
}


def bits_to_runs(bits: str) -> list:
    """Convert a '1'/'0' bitstring into an alternating run-length list,
    always starting with the space(1)-run count (0 if the row starts
    filled). This is the format you described: [2, 2, 2, 4] = 2 space,
    2 fill, 2 space, 4 fill."""
    runs = []
    expect_space = True
    i = 0
    while i < len(bits):
        j = i
        want = "1" if expect_space else "0"
        if bits[i] != want:
            runs.append(0)
            expect_space = not expect_space
            continue
        while j < len(bits) and bits[j] == want:
            j += 1
        runs.append(j - i)
        i = j
        expect_space = not expect_space
    return runs


def bits_to_ascii(bits: str) -> str:
    return bits.replace("1", ".").replace("0", "#")


def self_check():
    """Verify every letter has exactly LETTER_HEIGHT rows of exactly
    LETTER_WIDTH characters, and print an ASCII preview (# = real text,
    . = forced gap) so you can sanity-check edits without any source text."""
    print("=== Self-check: shape + dimensions ===\n")
    errors = []
    for ch, rows in FONT_BITMAPS.items():
        if len(rows) != LETTER_HEIGHT:
            errors.append(f"{ch!r} has {len(rows)} rows, expected {LETTER_HEIGHT}")
            continue
        print(f"--- {ch!r} ---")
        for row_i, bits in enumerate(rows):
            if len(bits) != LETTER_WIDTH or not re.fullmatch(r"[01]+", bits):
                errors.append(f"{ch!r} row {row_i}: {bits!r} is not a {LETTER_WIDTH}-char '0'/'1' string")
                print(f"(broken: {bits!r})")
                continue
            print(bits_to_ascii(bits))
        print()
    if errors:
        print("=== ERRORS ===")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print("All letters OK.\n")


def insert_at_index(original_str: str, insert_str: str, index: int) -> str:
    """Inserts a substring into a string at a specified index."""
    # Handle negative indices or indices that exceed string length gracefully
    return original_str[:index] + insert_str + original_str[index:]

def main():
    self_check()

    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=None, help="print the run-length view of one letter and exit")
    args = ap.parse_args()

    if args.runs:
        ch = args.runs
        print(f"Run-length view of {ch!r}:")
        for bits in FONT_BITMAPS[ch]:
            print(" ", bits_to_runs(bits), " ->", bits_to_ascii(bits))
        return

    source_text = build_themed_source(repeats=20000)

    flag = "flag{WEIRD_SPACING}"
    line_len = LINE_LEN
    gap_len = 12
    line = 10
    for char in flag:
        for code in (FONT_BITMAPS[char]):
            for dup in range(2):  # draw each bitmap row twice -> 2 horizontal lines per row
                start = line_len//4
                index = line_len*line
                for i,bit in enumerate(code):
                    if bit == "0":
                        continue
                    else:
                        source_text = insert_at_index(source_text," "*gap_len,index+start+gap_len*i)

                line = line+1
        line+=1

    file_name = "output.txt"

    # This creates 'output.txt' in the same folder as your Python script
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(source_text)

    print(f"File successfully saved locally as {file_name}")



if __name__ == "__main__":
    main()
