# Constellation

**Category:** ICS
**Difficulty:** Medium
**Author:** Voyager 1

## Description (what the competitor will see)

A Modbus/TCP device at `<challenge-host>:502` is exposing a set of
holding registers, but they don't look like normal telemetry — hundreds
of small integers in tight groups of three.

Read them, figure out what each group of three means, and plot it.

## Files Provided

- None — connect directly to the Modbus/TCP service.

## Flag

`flag{polaris_lock}`

## Solution

1. Player connects to the Modbus/TCP service and reads holding register
   1 — it holds `N`, the total number of points, and tells them how big
   subsequent batch reads need to be (staying under the 125-register
   Modbus read limit).
2. Player reads the rest of the register space and notices it comes in
   repeating groups of three starting at address 2: `X`, `Y`, `pen` for
   each point `i` at addresses `2 + i*3`, `3 + i*3`, `4 + i*3`.
3. Player figures out `pen` is a draw/lift flag: `pen = 0` means lift the
   pen and move to `(X, Y)` without drawing; `pen = 1` means draw a line
   from the previous point to `(X, Y)`.
4. Player plots all `N` points in order following that rule. The
   resulting connected line art spells out the flag as text.

## Solve Script

See `solution/solve.py`. Run it against the live service:

```bash
python solution/solve.py <challenge-host> 502
```

It reads all points in batches, plots them with matplotlib, and saves
`solution/flag.png` showing the flag rendered as connected dots.

## Techniques / Tags

`modbus`, `visual-decode`, `connect-the-dots`

## Setup / Deployment Notes

The register data isn't hand-crafted — `src/gen_coords.py` renders the
flag text with matplotlib, simplifies the resulting glyph outlines with
Ramer–Douglas–Peucker, and emits `(x, y, pen)` triplets.

```bash
cd src
python -m venv venv        # if not already present
./venv/Scripts/pip install -r requirements.txt
./venv/Scripts/python gen_coords.py "flag{polaris_lock}"
```

This writes `src/coordinates.json` (consumed by `server.py` / the
Dockerfile) and `src/preview.png` so you can eyeball the result before
shipping it. Output paths are resolved relative to the script's own
location, so it can be run from any working directory.

Run the server directly:

```bash
cd src
python server.py --port 5020 --coords coordinates.json
```

Or via Docker (`Dockerfile` bakes in whatever `coordinates.json` exists
at build time — regenerate it *before* building the image):

```bash
cd src
./run_docker.ps1 -Flag "flag{polaris_lock}" -Port 502
```

To reuse this challenge shape for a different event: change the flag
text passed to `src/gen_coords.py`, regenerate `coordinates.json`, and
rebuild the Docker image.

## Known Issues / Notes

None.
