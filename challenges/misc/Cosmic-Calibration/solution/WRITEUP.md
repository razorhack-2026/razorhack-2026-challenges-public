# Cosmic Calibration — Solution

**Category:** Misc
**Difficulty:** Med
**Author:** WALL-D

## Description (what the competitor will see)

See [../README.md](../README.md) and `description` in [../challenge.yml](../challenge.yml).

## Files Provided

- `dist/calibration_sequence` — a stripped Linux x86-64 binary (Nuitka onefile of
  `src/rubik2d.py`).
- `dist/RUN.md` — how to run the binary or reach the browser panel.
- A hosted browser panel (`src/web/`, see Setup / Deployment Notes) for every other OS.

## Flag

`flag{@11_@x!$_@1!gn3d_:D}`

Not stored as text anywhere. It is XOR-sealed (`FLAG_SEALED` in `rubik2d.py`) with a keystream
derived from the **solved** cube's state, and only decodes when the live cube is actually solved
(`reveal_flag` → `state_key` → SHA-256 of the solved stickers).

## Solution

The window shows 54 coloured dots arranged as nine concentric rings — this is a **3×3×3 Rubik's
cube** in disguise. Each axis owns a family of three circles (one per layer); every sticker sits
where two circles cross, so each dot belongs to two rings at once. Turning a layer slides its ring
of dots around and spins the face dots. The puzzle starts scrambled; restoring every face to one
colour reveals the flag.

1. **Recognize the encoding.** Nine rings of twelve dots, six colours, dots that move in rings when
   you press `U D L R F B` (and `M E S`, `X Y Z`) — it's a Rubik's cube rendered as circles. The
   start screen (`assets/cube_solved.png`) shows the solved target.
2. **Solve it.** Two realistic paths:
   - **By hand** in the window, using the move keys (Shift = inverse). Any normal cube method works
     once you map the dots to facelets.
   - **By scripting** the move engine: the notation (`parse`) and the `Cube` model in `rubik2d.py`
     are standard, so a competitor who reverses the state can feed a solver's solution as a move
     string: `./calibration_sequence "R U R' U' ..."` replays it, and solving reveals the flag.
     On the hosted panel the same string goes to `POST /api/moves` as `{"moves": "R U R' U' ..."}`.
3. **Read the flag** off the solved screen ("The control panel has been recalibrated").

## Solve Script

No solver is shipped to competitors (that would hand over the answer). `solution/solve_web.py`
(GM-only) solves the hosted panel: it replays the inverse of the fixed `SEED` scramble through
`/api/moves` and prints the flag. For the binary, verification uses the game's own engine: scramble,
apply the inverse, confirm `solved()` and that `reveal_flag` decodes.

Verified on 2026-11-05 (hosted panel, `docker compose up --build`):
- `python3 solution/solve_web.py` recovers the exact flag in `challenge.yml`, and so does a full
  solve typed on the keyboard in headless Chromium.
- A scrambled panel returns no flag. Finishing in another whole-cube orientation still returns the
  exact flag, and two cookies keep independent panels.
- `/rubik2d.py`, `/server.py` and traversal paths return 404, and the served HTML and JS contain no
  flag, no `FLAG_SEALED` hex, and no "cube" wording. Bad or oversized move strings return 400.

Verified on 2026-11-04 (public `PUBLIC_BUILD` binary):
- `./calibration_sequence --help` runs and lists no `--debug`; `./calibration_sequence --debug` is
  rejected (`unrecognized arguments: --debug`). The binary runs (e.g. `--gif` replays a move string).
- In `src/`: `reveal_flag(Cube())` on a fresh solved cube decodes to the flag above (starts with
  `flag{`), and a random 15-move scramble leaves `Cube.solved()` False until the inverse is applied —
  the `PUBLIC_BUILD` edit does not touch the cube model or the seal.

## Techniques / Tags

`rubiks-cube`, `encoding-recognition`, `puzzle`, `reverse-engineering`

## Setup / Deployment Notes

- **Host the browser panel:** `docker compose up --build -d` from this folder serves it on port
  8082, and `connection_info` in `challenge.yml` points competitors at it. No `FLAG` env var is
  needed: `src/web/server.py` imports `src/rubik2d.py` and uses the same seal as the binary.
- **Why the panel is server-side:** the cube and the seal stay in the container, and the page only
  draws the dot positions the server sends. Compiling `rubik2d.py` to WASM (e.g. pygbag) would ship
  `FLAG_SEALED` and the key derivation to the browser, where `reveal_flag(Cube())` gives the flag
  without solving anything. Don't swap it for that.
- Each player's panel is in memory, keyed by a cookie, so restarting the container resets everyone's
  progress. Run a single instance: replicas behind a load balancer won't share panels.
- The Linux binary opens a pygame window, so it needs a desktop session. It is the only binary
  shipped. Nuitka can't cross-compile, so Windows/macOS builds would each need a build on that OS.
  The browser panel covers those players instead.
- To change the flag: `python src/seal_flag.py 'flag{new}'`, paste the hex into `FLAG_SEALED` in
  `src/rubik2d.py`, rebuild (`python src/build.py`, or `src/build_public.sh` on Linux), recopy into
  `dist/`, and rebuild the container. Keep `challenge.yml`'s flag in sync.
- Linux build quirks (handled by `build.py`): Nuitka needs `patchelf` **0.17.x** (system 0.18.0 is
  rejected as buggy — `pip install 'patchelf==0.17.2.1'`), and the build passes `--lto=no` (LTO
  triggers an `undefined reference to entry_PIL` link error with Pillow). Build foreground or under
  `setsid` — Nuitka re-execs itself, which a job-control background runner can tear down mid-compile.

## Known Issues / Notes

- **Unintended solve (the `--debug` flag) — FIXED in the shipped build.** `rubik2d.py` has a
  suppressed `--debug` option that would enable a 3D view and **Space = instant solve**. The public
  binary in `dist/` is now built with `PUBLIC_BUILD = True` (near the bottom of `src/rubik2d.py`),
  which does not register `--debug` at all, so `./calibration_sequence --debug` is rejected
  (`error: unrecognized arguments: --debug`) and there is no Space-solve path. Verified against the
  shipped binary. To make a private GM debug build, flip `PUBLIC_BUILD = False` and rebuild — never
  ship that one. The browser panel has no equivalent: `src/web/server.py` has no debug or solve route.
- The flag is never in the binary as plaintext; solving (or reversing `state_key` and the seal) is
  required.
