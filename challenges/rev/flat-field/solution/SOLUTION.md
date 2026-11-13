# Flat Field — Solution (GM only)

**Flag:** `flag{the_mask_was_the_message}`

## What players get

| File | What it is |
|---|---|
| `condor_cal.png` | 1920x1080 RGB frame with a hidden CAL1 mask in the blue channel's low 2 bits |
| `lenscal` | Stripped, statically linked x86-64 Linux ELF that embedded the mask (`usage: lenscal <frame.png> <mask.cal> <out.png>`) |

The mask file itself (`src/mask.cal`) is not shipped, so running `lenscal` gets players nothing
directly. The flag is not present as text in either file.

## Solve path

1. **Triage.** `file` shows a static, stripped ELF. `strings` gives the usage line, the
   error messages, a stray `CAL1` (the magic's immediate bytes) ("bad calibration mask", "frame too small for mask"), and
   lots of stb_image/PNG text. Most of the binary is statically linked stb_image + musl;
   `main` is the only interesting code. Finding it via the usage string's xref is the fast way in.

2. **Mask format (from the header checks in `main`).**
   - bytes 0–3 compared to `0x314C4143` → magic `"CAL1"`
   - u16 at +4, u16 at +6 → `mw`, `mh`
   - file length must equal `8 + ceil(mw*mh/8)` → the body is a 1-bit `mw x mh` bitmap
   - capacity check: `len*8 <= w*h/4`

3. **Seed.** A loop over every pixel reads byte `i*3` (red) into FNV-1a 32
   (`0x811C9DC5` offset, `0x01000193` prime), then `^= (w<<16)|h`, then `^= 0x4C454E53`
   (`"LENS"`), with 0 replaced by 1. Only blue is ever written, so the seed computed from the
   calibrated frame equals the original seed. This is the key insight.

4. **PRNG.** xorshift32 with shifts 13 / 17 / 5. These are the recognisable constants.

5. **Embedding loop**, one iteration per bit of the *whole* mask file (header included),
   MSB-first:
   - `idx = rng() % (w*h)`, redrawn while `used[idx]` is set (no pixel is reused)
   - `k = rng() & 3`
   - blue low 2 bits ← `k` for a 0 bit, `k ^ 3` (inverted) for a 1 bit

   Decoding is `bit = ((blue & 3) ^ k) == 3`. Any XOR result of 1 or 2 means the solver
   has desynced (wrong seed, wrong draw order, or forgot the reuse skip). That gives players a
   built-in correctness check.

6. **Reconstruction.** Decode the first 64 bits → `CAL1`, `442`, `39`. Pull
   `ceil(442*39/8)*8` more bits, reshape the first `442*39` into a 39-row by 442-column
   bitmap, and render it. The flag is drawn as text in the image.

Reference: `python solution/solve.py dist/condor_cal.png mask.png` writes `mask.png`
(3x-scaled) showing the flag. Runtime is a few seconds (pure-Python FNV over 2M pixels).

## Pitfalls players will hit (all genuine, no decoys)

- Hashing all three channels, or hashing only the frame's own hash without the `w/h` and
  `"LENS"` XORs, gives the wrong seed and an immediate desync.
- Forgetting the `used[]` redraw. It works for the first few hundred bits, then desyncs
  once a collision happens. The 1/2 XOR values show exactly where.
- Forgetting the `k` draw between positions, which shifts the whole stream.
- Treating the header as unencoded (it's embedded with the same stream as the body).
- Row-major vs column-major when rendering. Wrong order gives noise, not text.

## Unintended paths considered

- **Diffing against NASA's original:** the frame is cropped, rescaled to 1080p and has seeded
  Gaussian noise (σ=2.5) added, so no clean original exists.
- **Black-box use of `lenscal`:** because the seed survives encoding, a player can run
  `lenscal condor_cal.png <crafted.cal> out.png` and diff outputs to learn pixel positions
  and `k` values, then decode. It still needs enough RE to craft a valid CAL1 file (the
  size/length checks only come from reading `main`), and recovering the draw order takes on the
  order of a thousand scripted runs of crafted mask lengths. That's valid but slower than reading
  `main`. We're accepting it as an alternate solve.
- **Visual inspection / LSB tools:** only the low 2 bits of blue change at about 13k scattered
  pixels, in PRNG order. Bit-plane viewers show noise.

## Rebuild

See `src/BUILD_NOTES.md`.
