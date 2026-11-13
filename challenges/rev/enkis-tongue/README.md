# Enki's Tongue

**Category:** Reverse Engineering
**Difficulty:** Hard
**Author:** Andy Roid

## Description

Deeper in the dig sits a second, older artifact — and it does not babble. It
answers only to an utterance that is consistent across its whole length: change
one syllable and the whole thing is wrong. Recovering the words is not the end —
the artifact then *speaks back* in a tongue keyed to what you said.

You are given `enkivm` (the artifact's interpreter) and `enki.nam` (the sealed
incantation). Feed your spoken words to it on stdin:

```
./enkivm enki.nam        # then type or pipe your incantation
```

Wrong words are met with silence. Reverse the interpreter, read the incantation,
and recover the one utterance that unbinds it. Speak it, and the artifact gives
up what it holds.

## Files Provided

- `enkivm` — the artifact's interpreter
- `enki.nam` — the sealed incantation it runs
- `SHA256SUMS` — checksums of the two files above

No network required.
