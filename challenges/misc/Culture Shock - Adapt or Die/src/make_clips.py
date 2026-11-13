"""Generate the reference-culture gallery for Culture Shock: Adapt or Die.

GM-only tool. It writes ``src/clips.json``, the hand-recorded observations the
web page serves at ``GET /clips``. The page replays these frames verbatim: it
contains no simulation code, so this is one of the only ways a competitor can
watch a colony change without spending a probe.

    python3 src/make_clips.py

The script also proves two things about the gallery and fails loudly otherwise:

  1. every recorded transition is consistent with this challenge's law; and
  2. the gallery alone does NOT pin the law down (otherwise it would be the
     answer key), while it DOES rule out B3/S23 — the law both earlier
     challenges in the sequence use, and the obvious wrong assumption.

"Consistent with" is decided by replaying every transition through a candidate
law, so the check is exhaustive over all 512 x 512 possible laws.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import ringlife

HERE = Path(__file__).resolve().parent

# Generations recorded per clip (the frame at index 0 is the starting colony).
# One step per vial: the archive only ever recorded a single transition, which
# is enough to show the colonies changing but not enough to identify the law
# (see the candidate count this script prints).
GENERATIONS = 1

# Every clip is drawn on the same small board so the gallery reads consistently.
COLS = 9
ROWS = 9

# The specimen layouts, as live coordinates. Each is centerd in the 9x9 board.
CLIPS = [
    {
        "id": "lone_spore",
        "name": "Lone spore",
        "note": "A single cell recovered from the asteroid core.",
        "cells": [(4, 4)],
    },
    {
        "id": "arm_in_arm",
        "name": "Two spores, arm in arm",
        "note": "Two cells, two apart — the closest they can be and still see each other.",
        "cells": [(4, 2), (4, 4)],
    },
    {
        "id": "tight_three",
        "name": "Three spores, touching",
        "note": "Three cells side by side.",
        "cells": [(4, 3), (4, 4), (4, 5)],
    },
    {
        "id": "old_blinker",
        "name": "The old blinker",
        "note": "The three-cell pattern every textbook calls a blinker.",
        "cells": [(4, 2), (4, 4), (4, 6)],
    },
    {
        "id": "old_block",
        "name": "The old block",
        "note": "The four-cell square every textbook calls a block.",
        "cells": [(4, 4), (4, 5), (5, 4), (5, 5)],
    },
    {
        "id": "halo",
        "name": "Halo",
        "note": "Sixteen cells in a ring, two out from the center.",
        "cells": [
            (4 + dy, 4 + dx)
            for dy in range(-2, 3)
            for dx in range(-2, 3)
            if max(abs(dx), abs(dy)) == ringlife.RING_RADIUS
        ],
    },
]


def build_frames(cells):
    """Return the recorded frames for one clip: GENERATIONS + 1 boards of rows."""
    board = [0] * (COLS * ROWS)
    for row, col in cells:
        board[row * COLS + col] = 1

    frames = []
    current = board
    for _ in range(GENERATIONS + 1):
        frames.append(
            [
                "".join("O" if current[row * COLS + col] else "." for col in range(COLS))
                for row in range(ROWS)
            ]
        )
        current = ringlife.step(current, COLS, ROWS)
    return frames


def observations(clips):
    """Every ``(alive, neighbour_count, next_alive)`` fact the gallery contains."""
    facts = set()
    for clip in clips:
        for index in range(len(clip["frames"]) - 1):
            before = ringlife.parse("\n".join(clip["frames"][index]))
            after = ringlife.parse("\n".join(clip["frames"][index + 1]))
            for cell in range(len(before.cells)):
                count = ringlife.count_neighbors(
                    before.cells, before.cols, before.rows, cell
                )
                facts.add((bool(before.cells[cell]), count, bool(after.cells[cell])))
    return facts


def law_satisfies(facts, birth, survive) -> bool:
    """True when a candidate law reproduces every recorded transition."""
    for alive, count, next_alive in facts:
        predicted = count in (survive if alive else birth)
        if predicted != next_alive:
            return False
    return True


def consistent_laws(facts):
    """Every (birth, survive) pair consistent with the recorded transitions."""
    counts = range(9)
    laws = []
    for size in range(10):
        for birth in itertools.combinations(counts, size):
            for s_size in range(10):
                for survive in itertools.combinations(counts, s_size):
                    if law_satisfies(facts, frozenset(birth), frozenset(survive)):
                        laws.append((frozenset(birth), frozenset(survive)))
    return laws


def main() -> None:
    clips = [
        {
            "id": clip["id"],
            "name": clip["name"],
            "note": clip["note"],
            "cols": COLS,
            "rows": ROWS,
            "frames": build_frames(clip["cells"]),
        }
        for clip in CLIPS
    ]

    facts = observations(clips)
    laws = consistent_laws(facts)

    if not law_satisfies(facts, ringlife.BIRTH, ringlife.SURVIVE):
        raise SystemExit("a recorded transition contradicts this challenge's law")

    if law_satisfies(facts, frozenset({3}), frozenset({2, 3})):
        raise SystemExit(
            "the gallery is consistent with B3/S23 — the wrong assumption would "
            "survive, not be exposed"
        )

    if len(laws) < 2:
        raise SystemExit(
            "the gallery alone identifies the law; competitors would never need "
            "to run a probe"
        )

    payload = {
        "generations": GENERATIONS,
        "clips": clips,
        "note": (
            "Recorded observations from the Keeper of Tomorrow's archive. "
            "Each frame is one generation: measured, not simulated."
        ),
    }
    (HERE / "clips.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    print(f"wrote src/clips.json: {len(clips)} clips x {GENERATIONS + 1} frames")
    print(f"recorded observations: {len(facts)} (state, count, next state) triples")
    print(f"laws consistent with the gallery: {len(laws)} of {2 ** 9 * 2 ** 9}")
    print("  B2/S2345 consistent: yes   B3/S23 consistent: no")

    # Report what the gallery leaves open, so the writeup is honest about what a
    # competitor still has to spend a probe on.
    births = {tuple(sorted(b)) for b, _ in laws}
    survives = {tuple(sorted(s)) for _, s in laws}
    print(f"  distinct candidate birth sets: {len(births)}")
    print(f"  distinct candidate survival sets: {len(survives)}")


if __name__ == "__main__":
    main()
