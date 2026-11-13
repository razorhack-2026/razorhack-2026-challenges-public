# Nothing to Report — Solution

## Real-world grounding

This is a **null cipher** — a hidden message carried by some structural property of
otherwise-innocent text, rather than by any mathematical transform. Null ciphers have real
historical use in espionage specifically because the carrier text looks mundane; the most
cited class of real-world examples are WWI/WWII-era messages smuggled past censors inside
ordinary-looking letters, where the hidden content rode on word-initial letters, word
positions, or similar textual properties rather than the letters' actual meaning.

## The encoding

Only the **body** of `dist/shift_log.txt` carries the message — everything after the first
blank line. The two header lines (title, "recovered from" note) are flavor, not signal; the
blank line is the competitor's visual cue for where the real document starts, since none of
the header words are meant to be decoded.

For each word in the body:
1. Strip leading/trailing punctuation (commas, periods).
2. Look at the first alphabetic character.
3. Vowel (`a/e/i/o/u`, case-insensitive) → bit `1`. Consonant → bit `0`.

Reading the words in order gives a bitstream. Grouped 8 bits at a time, **MSB-first**, that's
the flag's raw ASCII bytes. See `src/generate_document.py` for the exact encoder (word banks,
bit order, sentence-chunking that never reorders or inserts/removes an encoding word).

184 words encode `flag{vowel_null_cipher}` (23 bytes × 8 bits = 184 bits exactly, no padding
needed).

## Solve path

1. Notice the body text reads oddly stilted sentence after sentence — a hint that word choice
   itself is meaningful, not just the content.
2. Recognize the header/body split (blank line) — only the body counts.
3. For each body word, strip punctuation and check its first letter: vowel vs. consonant.
4. Group the resulting bits 8 at a time, MSB-first, decode as ASCII.

The real friction is in steps 2–4, not in spotting that something's encoded — getting the
header/body boundary, the punctuation-stripping, and the bit order all exactly right is what
separates a clean solve from a scrambled-looking almost-flag.

## Verification

Ran `src/generate_document.py` to produce `dist/shift_log.txt`, then ran
`solution/solve.py` against that file and got back the exact flag from `challenge.yml`:
`flag{vowel_null_cipher}`. Leak check (`grep -r "flag{" dist/ README.md`) clean — the only
real flag lives in `challenge.yml` and here.
