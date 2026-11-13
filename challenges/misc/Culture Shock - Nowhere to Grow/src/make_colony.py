"""Generate the Culture Shock - Nowhere to Grow colony and the reference removal set.

GM-only tool. It writes:

  src/colony.txt       -- the colony the server validates removals against
  dist/colony.txt      -- the competitor handout (identical board)
  solution/removal.txt -- the board to submit (colony after the removals)
  solution/removals.txt-- the removed cells, as human-readable coordinates

The board is built deterministically, so re-running this script reproduces the same challenge:

  * the interior is a 5x5 ring that expands over the first few generations before settling into a 13x13 still life, plus three 4x4 blocks. It stays well clear of the exclusion border for all 20 generations.
  * each side of the colony has a line of 13 cells on the innermost safe row / column, spaced two apart. Consecutive triples in that line overlap, and on the next generation the line births 11 live cells in the exclusion border.
  * because the birth windows overlap, one removal can cancel up to three neighbouring births. Each 13-cell line needs exactly 4 removals (4 sides x 4 = REMOVAL_LIMIT). The reference solution removes offsets 2, 5, 8, 11 of each line, which is one optimal hitting set.

    python3 src/make_colony.py
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import ringlife

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent

BOARD_COLS = 34
BOARD_ROWS = 34

# Interior: a radius-2 ring (16 cells) centred here expands to a 13x13 still life (rows/cols 5..17) during generations 1-3.
CORE_RING_CENTER = (11, 11)

# Top-left corners of three 4x4 blocks filling the other interior corners.
CORE_BLOCKS = ((8, 22), (22, 8), (22, 22))

# Threat lines: 13 cells at odd coordinates 5..29 on the innermost safe row or column. Starting at 5 keeps every line at least Chebyshev distance 3 from the perpendicular lines, so the four sides evolve independently.
THREAT_COORDS = tuple(range(5, 30, 2))  # 5, 7, ..., 29

# 0-based offsets into a 13-cell line whose removal hits every birth window.
SOLUTION_OFFSETS = (2, 5, 8, 11)


def _index(row: int, col: int) -> int:
    return row * BOARD_COLS + col


def build_colony():
    """Return ``(cells, threat_lines)`` for the deterministic colony."""
    cells = [0] * (BOARD_COLS * BOARD_ROWS)

    # Evolving interior ring.
    centre_row, centre_col = CORE_RING_CENTER
    for row in range(centre_row - 2, centre_row + 3):
        for col in range(centre_col - 2, centre_col + 3):
            if max(abs(row - centre_row), abs(col - centre_col)) == 2:
                cells[_index(row, col)] = 1

    # Interior still-life blocks.
    for top, left in CORE_BLOCKS:
        for row in range(top, top + 4):
            for col in range(left, left + 4):
                cells[_index(row, col)] = 1

    # Overlapping threat lines on the innermost safe row/column of each side.
    threat_lines = [
        [(2, col) for col in THREAT_COORDS],                          # top
        [(BOARD_ROWS - 3, col) for col in THREAT_COORDS],             # bottom
        [(row, 2) for row in THREAT_COORDS],                          # left
        [(row, BOARD_COLS - 3) for row in THREAT_COORDS],             # right
    ]

    for line in threat_lines:
        for row, col in line:
            cells[_index(row, col)] = 1

    return cells, threat_lines


def build_solution(cells, threat_lines):
    """Remove one optimal hitting set from each overlapping threat line."""
    solved = list(cells)
    removed = []
    for line in threat_lines:
        for offset in SOLUTION_OFFSETS:
            row, col = line[offset]
            index = _index(row, col)
            if solved[index]:
                solved[index] = 0
                removed.append((row, col))
    return solved, removed


def min_line_removals(length: int) -> int:
    """Minimum cells to remove from one threat line to hit every birth window.

    Window ``i`` needs cells ``i``, ``i+1`` and ``i+2`` all live, so a removal hits windows i-2..i. A 13-cell line has 11 windows.
    """
    windows = [set(range(start, start + 3)) for start in range(length - 2)]
    for count in range(length + 1):
        for combo in combinations(range(length), count):
            chosen = set(combo)
            if all(chosen & window for window in windows):
                return count
    return length


def main() -> None:
    cells, threat_lines = build_colony()

    colony = ringlife.Board(BOARD_COLS, BOARD_ROWS, 0, tuple(cells))

    if not ringlife.is_contained(colony.cells, colony.cols, colony.rows):
        raise SystemExit("generated colony is not contained at generation 0")

    initial_breach, _ = ringlife.first_breach(
        colony.cells, colony.cols, colony.rows
    )
    if initial_breach is None:
        raise SystemExit("generated colony never breaches — no puzzle")

    solved_cells, removed = build_solution(cells, threat_lines)
    solved = ringlife.Board(BOARD_COLS, BOARD_ROWS, 0, tuple(solved_cells))

    minimum = sum(min_line_removals(len(line)) for line in threat_lines)
    if minimum != ringlife.REMOVAL_LIMIT:
        raise SystemExit(
            f"true minimum is {minimum} removals but REMOVAL_LIMIT is "
            f"{ringlife.REMOVAL_LIMIT} — update one to match"
        )

    if len(removed) > ringlife.REMOVAL_LIMIT:
        raise SystemExit(
            f"reference solution removes {len(removed)} cells, "
            f"over the {ringlife.REMOVAL_LIMIT}-cell limit"
        )

    breach, _ = ringlife.first_breach(solved.cells, solved.cols, solved.rows)
    if breach is not None:
        raise SystemExit(
            f"reference solution still breaches at generation {breach}"
        )

    if not ringlife.is_contained(solved.cells, solved.cols, solved.rows):
        raise SystemExit("reference solution is not contained at generation 0")

    colony_text = ringlife.serialize(colony)
    (HERE / "colony.txt").write_text(colony_text, encoding="utf-8")

    dist_dir = CHALLENGE / "dist"
    dist_dir.mkdir(exist_ok=True)
    (dist_dir / "colony.txt").write_text(colony_text, encoding="utf-8")

    solution_dir = CHALLENGE / "solution"
    solution_dir.mkdir(exist_ok=True)
    (solution_dir / "removal.txt").write_text(
        ringlife.serialize(solved), encoding="utf-8"
    )

    lines = [
        "# cells removed from dist/colony.txt (0-based row,column)",
        f"# count: {len(removed)} (limit {ringlife.REMOVAL_LIMIT})",
    ]
    lines.extend(f"{row},{col}" for row, col in removed)
    (solution_dir / "removals.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(
        f"colony: {colony.alive()} alive, breaches at generation {initial_breach} "
        f"without removals ({BOARD_COLS}x{BOARD_ROWS})"
    )
    print(
        f"per-side minimum removals: "
        f"{[min_line_removals(len(line)) for line in threat_lines]}"
    )
    print(
        f"reference solution: remove {len(removed)} cells -> "
        f"{solved.alive()} alive, contained for "
        f"{ringlife.CONTAINMENT_GENERATIONS} generations"
    )


if __name__ == "__main__":
    main()
