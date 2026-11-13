#!/usr/bin/env python3
"""
Generates dist/shift_log.txt for "Nothing to Report".

Encoding (GM-only knowledge, documented in solution/solution.md, NOT in the
competitor README): for each word in the body text, look at its first
alphabetic character. Vowel (a/e/i/o/u, case-insensitive) = bit 1,
consonant = bit 0. Reading the words in order gives a bitstream; grouped
8 bits at a time, MSB-first, that's the flag's raw bytes.

Only alphabetic words with no apostrophes/hyphens are used in the word
banks, specifically to keep "what counts as a word" unambiguous once you
strip surrounding punctuation (commas/periods) from each token.
"""
import os
import random
import textwrap

FLAG = "flag{vowel_null_cipher}"

# Plausible, slightly-stilted shift-log vocabulary. Kept deliberately plain
# (no contractions/hyphens) so stripping trailing punctuation is the only
# normalization a competitor needs.
VOWEL_WORDS = [
    "air", "alarm", "another", "area", "around", "assigned", "automatic",
    "each", "early", "empty", "even", "every", "exact", "export",
    "idle", "inbound", "inside", "instrument", "into", "issue",
    "odd", "offline", "once", "online", "open", "outbound", "overdue",
    "under", "until", "unusual", "update", "upper",
]
CONSONANT_WORDS = [
    "backup", "bay", "board", "break", "bridge",
    "cable", "cargo", "check", "crew", "cycle",
    "deck", "door", "duty",
    "found", "fuel",
    "gauge", "gate",
    "hatch", "hold", "hull",
    "late", "light", "line", "log", "loop",
    "main", "measured", "module",
    "night", "noted", "normal",
    "panel", "pump",
    "quiet",
    "ran", "ready", "record", "round",
    "sealed", "shift", "stable", "status", "system",
    "tank", "test", "tight",
    "valve", "vent",
    "watch", "window",
]


def word_for_bit(bit: int, rng: random.Random) -> str:
    return rng.choice(VOWEL_WORDS if bit else CONSONANT_WORDS)


def flag_to_bits(flag: str) -> list:
    bits = []
    for ch in flag.encode("ascii"):
        for i in range(7, -1, -1):  # MSB-first
            bits.append((ch >> i) & 1)
    return bits


def build_body(words: list) -> str:
    # Chunk into sentence-ish groups (6-10 words) without reordering or
    # adding/removing any encoding word. Capitalization/punctuation added
    # here never changes a word's first ALPHABETIC character.
    rng = random.Random(1337)
    sentences = []
    i = 0
    while i < len(words):
        n = rng.randint(6, 10)
        chunk = words[i:i + n]
        i += n
        if not chunk:
            continue
        s = " ".join(chunk)
        s = s[0].upper() + s[1:] + "."
        sentences.append(s)
    paragraph = " ".join(sentences)
    return "\n".join(textwrap.wrap(paragraph, width=78))


def main():
    rng = random.Random(42)
    bits = flag_to_bits(FLAG)
    words = [word_for_bit(b, rng) for b in bits]
    body = build_body(words)

    header = (
        "RAZORPOWER CO. -- DOCKING RING 3 -- CREW SHIFT LOG\n"
        "Entry recovered from logger cm-0417's backup partition.\n"
        "\n"
    )

    out_path = os.path.join(os.path.dirname(__file__), "..", "dist", "shift_log.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="\n") as f:
        f.write(header + body + "\n")

    print(f"Wrote {len(words)} words ({len(bits)} bits) to {out_path}")


if __name__ == "__main__":
    main()
