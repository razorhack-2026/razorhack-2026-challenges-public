"""Reference solution for Culture Shock: Adapt or Die.

The growth law is not in the browser, so it has to be measured. One observation
is enough: a single board can hold eighteen independent cultures, one for every
neighbour count a radius-2 ring can hold (0-8), in two flavours — a dead center
and a live center. Spacing the sites six apart keeps every ring private, so the
whole truth table falls out of one image.

    python3 solution/solve.py [--url http://localhost:40819]

Steps:

  1. observe the handout specimen for one generation (also a cross-check later);
  2. observe the eighteen-site truth-table board;
  3. read the law off the centers, verify it reproduces the specimen transition,
     and print the notation;
  4. submit the notation and print the flag.

Uses three of the twelve doses of reagent.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent
sys.path.insert(0, str(CHALLENGE / "src"))

import ringlife  # noqa: E402  (path set up above)

# Distance between probe sites. A radius-2 ring reaches two cells, so sites must
# be at least seven apart: at six, one site's ring cells sit exactly two cells
# from its neighbour's ring cells and the two questions contaminate each other.
SITE_PITCH = 7
SITE_OFFSET = 3

# Six sites across, three down: eighteen questions on one board.
SITE_COLS = 6
SITE_ROWS = 3

COLS = SITE_COLS * SITE_PITCH
ROWS = SITE_ROWS * SITE_PITCH

RING = ringlife.ring_offsets(ringlife.RING_RADIUS)


def site_center(index: int):
    """Row/column of the center of probe site ``index``."""
    return (
        SITE_OFFSET + (index // SITE_COLS) * SITE_PITCH,
        SITE_OFFSET + (index % SITE_COLS) * SITE_PITCH,
    )


def build_probe_board() -> ringlife.Board:
    """One board holding every (center state, neighbour count) question."""
    cells = [0] * (COLS * ROWS)

    for index in range(SITE_COLS * SITE_ROWS):
        row, col = site_center(index)
        # First nine sites: a dead center. Last nine: a live center. The site's
        # index inside its half is the neighbour count it is asking about.
        count = index % 9
        alive_center = index >= 9

        if alive_center:
            cells[row * COLS + col] = 1

        for dx, dy in RING[:count]:
            cells[(row + dy) * COLS + (col + dx)] = 1

    return ringlife.Board(COLS, ROWS, 0, tuple(cells))


def read_law(board: ringlife.Board):
    """Recover ``(birth, survive)`` from the centers of the answered probe board."""
    birth = set()
    survive = set()

    for index in range(SITE_COLS * SITE_ROWS):
        row, col = site_center(index)
        count = index % 9
        center_alive = bool(board.cells[row * board.cols + col])
        if index >= 9:
            if center_alive:
                survive.add(count)
        elif center_alive:
            birth.add(count)

    return frozenset(birth), frozenset(survive)


class Lab:
    """Minimal client for the calibration service, keeping one session cookie."""

    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def _post(self, path: str, body: bytes, content_type: str) -> dict:
        request = urllib.request.Request(
            self.base + path,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise SystemExit(f"server rejected the request (HTTP {exc.code}): {detail}")
        except urllib.error.URLError as exc:
            raise SystemExit(f"could not reach {self.base}: {exc.reason}")

    def observe(self, board: ringlife.Board, generations: int = 1) -> ringlife.Board:
        """Ask the rig to run a culture forward; costs one dose of reagent."""
        result = self._post(
            f"/observe?generations={generations}",
            ringlife.serialize(board).encode("utf-8"),
            "text/plain",
        )
        if result.get("status") != "ok":
            raise SystemExit(f"observation failed: {result.get('message')}")
        print(
            f"  observed {generations} generation(s): "
            f"{result['remaining']} dose(s) left",
            file=sys.stderr,
        )
        return ringlife.parse(result["state"])

    def submit(self, notation: str) -> dict:
        """Propose a growth law; costs one dose of reagent."""
        return self._post(
            "/submit",
            json.dumps({"rule": notation}).encode("utf-8"),
            "application/json",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve Culture Shock: Adapt or Die")
    parser.add_argument("--url", default="http://localhost:40819")
    args = parser.parse_args()

    specimen = ringlife.parse(
        (CHALLENGE / "dist" / "specimen.txt").read_text(encoding="utf-8")
    )
    print(
        f"specimen: {specimen.cols}x{specimen.rows}, {specimen.alive()} alive",
        file=sys.stderr,
    )

    lab = Lab(args.url)

    print("observing the specimen for one generation...", file=sys.stderr)
    specimen_next = lab.observe(specimen, 1)

    print("observing the eighteen-site truth-table board...", file=sys.stderr)
    probe = build_probe_board()
    answered = lab.observe(probe, 1)

    birth, survive = read_law(answered)
    notation = ringlife.format_rule(birth, survive)
    print(f"measured law: {notation}", file=sys.stderr)

    # The handout is an independent check: the measured law must reproduce the
    # specimen's transition too, or the measurement was misread.
    predicted = ringlife.step(specimen.cells, specimen.cols, specimen.rows,
                              birth, survive)
    if tuple(predicted) != tuple(specimen_next.cells):
        raise SystemExit(
            "measured law does not reproduce the specimen's transition — the "
            "probe board was misread"
        )
    print("cross-check against the handout: matches", file=sys.stderr)

    print(f"submitting {notation}...", file=sys.stderr)
    result = lab.submit(notation)
    print(json.dumps(result, indent=2))

    if not result.get("flag"):
        raise SystemExit("no flag returned — the proposed law was not accepted")


if __name__ == "__main__":
    main()
