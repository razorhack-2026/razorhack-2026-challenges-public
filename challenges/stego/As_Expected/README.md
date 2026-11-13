# As Expected

**Category:** Steganography
**Difficulty:** Medium
**Author:** Voyager 1

## Description

A terminal buffer dump recovered from an old relay station export — one giant,
unbroken block of text. No line breaks, just operational chatter running on and on.
Whoever first opened it took one look, saw "status nominal" repeated a thousand
times, and moved on.

They were looking at it wrong.

The export came with a block validator: a checksum over the first chunk of the
dump, confirming it hasn't been corrupted. The terminal never recorded how big a
chunk it was checking.

## Files Provided

- `dist/output.txt` — the raw terminal buffer dump.
- `dist/checksum.txt` — the block validator's checksum.
- `dist/viewer.html` — open this locally in any browser. Upload `output.txt`,
  type in a chars-per-line width, and it re-wraps the dump live. No install,
  no server, nothing to write yourself — just load the file and give it a number.

## Flag Format

`flag{...}`
