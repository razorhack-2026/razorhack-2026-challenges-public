"""Generate the recovered specimen handed out as ``dist/specimen.txt``.

GM-only tool. It writes the same board to two places:

  src/specimen.txt  -- what the challenge server serves at GET /specimen
  dist/specimen.txt -- the competitor handout

The specimen is a *mixture*: one lone spore, one pair at arm's length, one trio
packed together and one solid square, kept far enough apart that they never see
each other. Watching the mixture evolve is interesting, and it says nothing
about the growth law on its own — that is what the probe lab and the recorded
gallery are for.

    python3 src/make_specimen.py
"""

from __future__ import annotations

from pathlib import Path

import ringlife

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent

COLS = 32
ROWS = 32

# Four cultures, spaced far apart: they are independent colonies in one vial.
CULTURES = [
    ("lone spore", [(6, 6)]),
    ("pair at arm's length", [(6, 24), (6, 26)]),
    ("trio packed together", [(16, 14), (16, 15), (16, 16)]),
    ("solid square", [(row, col) for row in range(24, 28) for col in range(6, 10)]),
]


def build() -> ringlife.Board:
    cells = [0] * (COLS * ROWS)
    for _, coordinates in CULTURES:
        for row, col in coordinates:
            cells[row * COLS + col] = 1

    board = ringlife.Board(COLS, ROWS, 0, tuple(cells))

    # Sanity: the vial must actually be alive, and must actually change.
    if board.alive() == 0:
        raise SystemExit("specimen is empty")
    if ringlife.evolve(board, 1).alive() == 0:
        raise SystemExit("specimen dies immediately — nothing to observe")

    return board


def main() -> None:
    board = build()
    text = ringlife.serialize(board)

    if "B3" in text or "S23" in text:
        raise SystemExit("serialized specimen mentions a growth law")

    for target in (HERE / "specimen.txt", CHALLENGE / "dist" / "specimen.txt"):
        target.write_text(text, encoding="utf-8")

    print(
        f"wrote specimen: {COLS}x{ROWS}, {board.alive()} live cells, "
        f"{len(CULTURES)} cultures"
    )
    print("  src/specimen.txt and dist/specimen.txt are identical")


if __name__ == "__main__":
    main()
