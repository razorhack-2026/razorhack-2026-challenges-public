# As Expected — Solution

## Real-world grounding

This is a **scytale**-style transposition trick: the hidden content isn't a mathematical
transform on the text, it's purely a property of how the text gets *laid out*. Wrap a flat
character stream at the wrong width and inserted gaps look like scattered noise; wrap it at
the exact right width and those same gaps line up into columns that form a picture. No width
is stated anywhere in the file on purpose — it has to be derived, not read off a line.

## The encoding

`dist/output.txt` is one unbroken blob of on-theme filler phrases. At a fixed chars-per-line
width of **3823**, oversized (12-character) whitespace gaps have been inserted at five
consistent columns (`start = width // 4`, then `start + 12*i` for `i` in 0..4) on specific
lines, forming a 5x7 bitmap font, one character at a time, spelling `flag{WEIRD_SPACING}`.
Each font row is drawn twice in a row (2 output lines per bitmap row), with one blank
separator line between characters. See `src/letter_gap_scaffold.py` for the exact generator
(`FONT_BITMAPS`, `LINE_LEN`, the gap-insertion loop).

## Finding the width

`dist/checksum.txt` gives a sha256 of "the first `BLOCK_SIZE` characters of the raw dump" but
never states `BLOCK_SIZE`. That's the oracle: hash every candidate prefix length against the
given checksum until one matches.

```python
import hashlib
with open("dist/output.txt", encoding="utf-8") as f:
    text = f.read().replace("\n", "")
for w in range(1, 10000):
    if hashlib.sha256(text[:w].encode()).hexdigest() == "82e61065f62169c6c3d95f1f6df09ed0f4560894bb5194d35d44e4f59e44c813":
        print(w)   # 3823
        break
```

This is the only intended discovery path. A visual/slider search across a 1–10000 range isn't
a realistic shortcut here — the correct width is too large and too specific to stumble on by
eye, and `dist/viewer.html`'s width field has to be typed, not dragged into place.

## Reading it

Once the width is known, no custom renderer is needed. Open `dist/viewer.html` in any
browser, upload `output.txt`, and type `3823` into the width field — it re-wraps the dump
live and the picture is immediately visible (or use `fold -w 3823 dist/output.txt` on the
command line, same result). `solution/solve.py` additionally automates the read-back: it
rewraps at the found width, checks five known columns per line for a real gap, and matches
each 7-row group against the font table to decode the flag programmatically.

## Verification

Ran `src/letter_gap_scaffold.py` to produce `dist/output.txt` (and the matching checksum in
`dist/checksum.txt`), then ran `solution/solve.py` against `dist/` only and got back the exact
flag from `challenge.yml`: `flag{WEIRD_SPACING}`. Leak check
(`grep -RnoE 'flag\{[^}]*\}' dist/ README.md`) clean — the only real flag lives in
`challenge.yml` and here.
