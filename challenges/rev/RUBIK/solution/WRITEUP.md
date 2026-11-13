# Complex Calibration — Solution

**Category:** Rev
**Difficulty:** Hard
**Author:** WALL-D

## Description (what the competitor will see)

See [../README.md](../README.md) and `description` in [../challenge.yml](../challenge.yml).

## Files Provided

- `dist/complex_calibration` — the challenge (Nuitka onefile of `src/tesseract3d.py`). Carries the
  sealed flag. **This is the only free download** (the only entry in `challenge.yml` `files:`).
- `dist/complex_calibration_tesseract` — the **helper** (onefile of `src/tesseract_helper.py`): the
  same game with the 4D "diagnostic" view always on and **no** Space-solve. It is **not** a free
  download — it is gated behind an **unlockable, point-cost hint** (see below). It still lives in
  `dist/` because the hosted deployment builds the browser view from it.
- When a team unlocks the hint they get the helper two ways: the **hosted browser view** (noVNC,
  see `deploy/` and `../docker-compose.yml`) and a **download link** to the helper binary. Both show
  the same no-auto-solve view, so unlocking hands over the *view*, not the flag.

## Flag

`flag{wh3n_7h3_$t@r$_@1!gn!}`

Same sealing scheme as the cube: XOR-sealed (`FLAG_SEALED` in `tesseract3d.py`) with a keystream
from the **solved** tesseract's state (`tesseract2d.state_key`), decoded only on a real solve.

## Solution

The panel is a **3×3×3×3 tesseract** — a 4D Rubik's cube — drawn in 3D. It has **eight cells**
(R L U D F B O I), each itself a 3×3×3 Rubik's cube ("galaxy" of a 3D shape). Solved means every
galaxy is home *and* every cell's faces are a single colour. The main view is hard to read in 3D
alone, which is the point of the diagnostic (4D) view.

1. **Use the diagnostic view.** The helper binary (or the hosted browser view) shows the real 4D
   debug layout always on — `Tab` toggles it, `H` shows/hides the O cell. This is how a competitor
   makes sense of eight cells instead of six faces and sees how a 4D twist (`X Y Z`, or `*`/`2`
   move prefixes) moves whole cells.
2. **Learn the moves.** Notation is in `tesseract2d.parse`: two-letter moves like `RU`, `FO'`,
   `*RO`, `2UF`, with `'` for inverse and `2` for a half turn; focus a cell (click or `1`–`8`) and
   the `U D L R F B` / `M E S` / `X Y Z` keys act on it.
3. **Solve by hand.** Restore every galaxy to home and every cell to solid faces. On the full solve
   the flag appears ("solving it shows the flag as usual").
4. **(RE alternative.)** As with the cube, a competitor who reverses `state_key` + the XOR seal can
   decode `FLAG_SEALED` directly from the solved-state key without playing — intended-adjacent and
   acceptable.

The helper does **not** auto-solve — it only makes the structure visible — so giving teams the
hosted view doesn't give away the flag.

## Solve Script

No packaged solver is shipped. Verification uses the game's own engine (scramble → inverse → solved
→ flag decodes).

Verified on 2026-11-04 (public `PUBLIC_BUILD` binary):
- `./complex_calibration --help` runs and lists no `--debug`; `./complex_calibration --debug` is
  rejected (`unrecognized arguments: --debug`). No `flag{` string appears in the binary.
- In `src/`: `tesseract3d.reveal_flag(Tesseract())` on a fresh solved tesseract decodes to the flag
  above; a random 15-move scramble leaves `Tesseract.solved()` False until the inverse is applied.
  The `PUBLIC_BUILD` edit touches only `main()`, not the model or the seal.
- The browser deployment (`deploy/`) is **not yet run end-to-end** here — see its caveats.

## Setup / Deployment Notes

- **Downloads (cross-platform):** the challenge binary is built for **Windows, macOS and Linux**
  from one source — see `Submission/BUILDING.md` and the CI matrix
  (`.github/workflows/rubiks2d-build.yml`); `src/build.py` builds both the challenge and the helper.
  Nuitka can't cross-compile, so the Windows/macOS artifacts come from CI runners (only Linux was
  built here). After CI, place the per-OS `complex_calibration` builds in `dist/`, add them to
  `challenge.yml` `files:`, and list them in the README. `dist/RUN.md` carries the per-OS run steps
  (incl. Gatekeeper/SmartScreen click-throughs for the unsigned builds). The helper needs OpenGL on
  whichever OS it runs; teams who can't run it use the hosted browser view below.
- **Hosted helper:** `../docker-compose.yml` + `deploy/` run the helper under Xvfb + software
  OpenGL and serve it over noVNC at `http://<host>:6080`, so teams without a local OpenGL setup can
  still see the 4D view. `deploy/README.md` has the run command and caveats (shared vs. per-team
  view, read-only option, the "black window = missing lib" check). **TODO(WALL-D): build and open
  it once before the event.**
- **Unlockable-hint delivery.** The helper is gated behind a point-cost hint in `challenge.yml`.
  CTFd hints are text only, so the hint carries two URLs the GM fills in at deploy time: the hosted
  noVNC view (`http://<host>:6080`) and a download link to `dist/complex_calibration_tesseract`
  hosted by the GM (e.g. a static path on the same box). The binary stays in `dist/` but is kept out
  of `challenge.yml` `files:` so CTFd does not publish it as a free download.
- **To change the flag:** `python src/seal_flag.py --tesseract 'flag{new}'`, paste the hex into
  `FLAG_SEALED` in `src/tesseract3d.py`, rebuild both binaries (`python src/build.py`, or
  `src/binary_creation.sh` on Linux; see the Cube writeup for the patchelf/`--lto=no` quirks),
  recopy into `dist/`, re-run CI for Windows/macOS, and rebuild the deploy image. Keep
  `challenge.yml` in sync.

## Known Issues / Notes

- **Unintended solve (the `--debug` flag) — FIXED in the shipped build.** `tesseract3d.py` has a
  suppressed `--debug` that would turn on the 4D view **and Space = instant solve**. The shipped
  `complex_calibration` is now built with `PUBLIC_BUILD = True`, which does not register `--debug`,
  so `--debug` is rejected and there is no Space-solve path (verified). The *helper* never had a
  Space-solve and never registered `--debug` (its argparse has only `moves`/`--width`), so it was
  already safe.
- **Spoiler in `--help` (recommend fixing).** The binary's argparse description prints
  "4D Rubik's cube (tesseract) in 3D", and the cube's prints "...Rubik's cube" — i.e. `--help`
  reveals exactly what `challenge.yml`/README deliberately hide, which for a Rev puzzle is most of
  the recognition step. If you want it hidden, change the `description=` string in
  `src/tesseract3d.py` (and `src/rubik2d.py`) to something neutral like "RASA calibration panel" and
  rebuild. Left as-is for now because it is a design call, not a correctness bug.
- **Shared hosted view.** The noVNC deployment shares one window among all visitors (see
  `deploy/README.md`); fine for an aid, but consider `-viewonly` or per-team containers if that
  matters.
- Flag never stored as plaintext in either binary (confirmed with `strings`).
