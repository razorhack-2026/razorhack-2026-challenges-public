# Field Diagnostic — solution (GM-only)

**Flag:** `flag{bytecode_still_reads_like_source}`
**Service code:** `svc-7731-unlock`

## Mechanism

`diagnostic.pyc` is a Python 3.8 compiled module. **No XOR is used** — the XOR
keystream pattern is already covered by other challenges (Silent Directive, Tool
Call Trail, pulsar-dropbox, thrust), so this one uses two different, plainly
readable primitives:

- **Service-code gate — bit rotation.** `_roll(code)` left-rotates each code
  byte by `_ROT` (3) bits and compares to `_TARGET`. So the service code is
  `_TARGET` with each byte **right-rotated** by 3.
- **Full readout — rotate + transpose.** `_SCRAMBLED` is the readout with each
  byte left-rotated by `_ROT`, then its bytes permuted into positions from a
  permutation seeded by the service code:
  `random.Random(int.from_bytes(code, "big")).shuffle(order)`. The rotation
  hides the byte values (the constant is garbage, not a readable anagram); the
  permutation hides their order. Recovering the code reproduces the permutation
  and un-rotates, giving the readout — which contains the flag. The `flag{`
  substring never appears in the shipped file.

## Intended solve

1. Recognize `diagnostic.pyc` as Python 3.8 bytecode (the `.pyc` magic) and
   decompile it — `uncompyle6`, `decompyle3`, or `pycdc` all handle 3.8:
   ```
   uncompyle6 diagnostic.pyc
   ```
2. Read the gate: `_roll` left-rotates by `_ROT = 3`, so recover the code by
   right-rotating each byte of `_TARGET` by 3 → `svc-7731-unlock`.
3. Reproduce the readout: build `order` from
   `random.Random(int.from_bytes(code, "big")).shuffle`, place each
   `_SCRAMBLED[i]` at `order[i]`, right-rotate each byte by 3, decode → the full
   readout ending in the flag. (Or just run the tool under Python 3.8 and type
   the recovered code at the prompt.)

## Reference solver

`solve.py` reads only `dist/diagnostic.pyc`. It marshals the code object out of
the `.pyc`, pulls the two byte constants from `co_consts`, and recovers the code
and flag by trying the rotation amount (it hardcodes no answer and imports
nothing from the builder). Because marshal is version-specific and the
`random.shuffle` must match the build, run it under Python 3.8:

```
uv run --python 3.8 python solve.py dist/diagnostic.pyc
# service code: svc-7731-unlock
# FLAG: flag{bytecode_still_reads_like_source}
```

Verified 2026-11-02: recovers the flag from the shipped `dist/` alone; the
program accepts the recovered code; a wrong code is rejected; the decompile is
clean and `_SCRAMBLED` exposes no readable flag characters.

## Rebuild

`uv run --python 3.8 python src/build.py` regenerates
`src/diagnostic_rendered.py` and `dist/diagnostic.pyc`. `src/build.py` holds the
service code and flag and must never ship; `src/` as a whole stays GM-only.
