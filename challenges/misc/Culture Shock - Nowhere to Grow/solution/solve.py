"""Reference solution for Culture Shock - Nowhere to Grow.

The solver reads the competitor handout ``dist/colony.txt``, finds a set of at most REMOVAL_LIMIT cells whose removal keeps every generation 0..20 free of live cells in the 2-cell exclusion border, verifies that locally, then submits the resulting board.

    python3 solution/solve.py [--url http://localhost:40818]

The rule is B3/S23 with the radius-2 neighbor ring and hard board edges.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent
sys.path.insert(0, str(CHALLENGE / "src"))

import ringlife  # noqa: E402


def live_ring_neighbors(cells, cols: int, rows: int, index: int):
    """Indices of live cells on the radius-2 ring around ``index``."""
    row, col = divmod(index, cols)
    neighbors = []
    for dx, dy in ringlife.ring_offsets():
        n_row, n_col = row + dy, col + dx
        if 0 <= n_row < rows and 0 <= n_col < cols:
            n_index = n_row * cols + n_col
            if cells[n_index]:
                neighbors.append(n_index)
    return neighbors


def greedy_removals(colony: ringlife.Board):
    """Remove cells that cause border births on the next generation.

    Every spark triple in the colony births a border cell on generation 1. Each such birth has exactly three live gen-0 ring neighbours (the triple); removing any one of them stops that birth. We pick the neighbour shared by the most births so a single removal resolves a whole group.
    """
    cols, rows = colony.cols, colony.rows
    cells = list(colony.cells)
    removed = set()

    for _ in range(ringlife.REMOVAL_LIMIT):
        generation, _violations = ringlife.first_breach(cells, cols, rows)
        if generation is None:
            return cells, removed

        next_cells = ringlife.step(cells, cols, rows)
        births = [
            index
            for index in ringlife.containment_violations(next_cells, cols, rows)
            if not cells[index]
        ]
        if not births:
            break  # breach is not on the next step; fall back to recorded set

        score = {}
        for birth in births:
            for neighbor in live_ring_neighbors(cells, cols, rows, birth):
                score[neighbor] = score.get(neighbor, 0) + 1

        if not score:
            break

        best = max(score, key=lambda index: (score[index], -index))
        cells[best] = 0
        removed.add(best)

    return cells, removed


def threat_lines(colony: ringlife.Board):
    """Group the live cells on each innermost safe boundary line.

    The colony's frontier cells sit on row = margin, row = rows-margin-1 and the equivalent columns. Returns four lists ordered along each side.
    """
    cols, rows = colony.cols, colony.rows
    margin = ringlife.CONTAINMENT_MARGIN

    def alive(row, col):
        return bool(colony.cells[row * cols + col])

    lines = [
        [(margin, col) for col in range(cols) if alive(margin, col)],
        [(rows - margin - 1, col) for col in range(cols)
         if alive(rows - margin - 1, col)],
        [(row, margin) for row in range(rows) if alive(row, margin)],
        [(row, cols - margin - 1) for row in range(rows)
         if alive(row, cols - margin - 1)],
    ]
    return [line for line in lines if line]


def hitting_sets(length: int, removals: int):
    """Every removal set that hits all consecutive-triple birth windows."""
    windows = [set(range(start, start + 3)) for start in range(length - 2)]
    found = []
    for combo in itertools.combinations(range(length), removals):
        chosen = set(combo)
        if all(chosen & window for window in windows):
            found.append(combo)
    # Prefer spread-out choices: they leave short, isolated leftover runs.
    found.sort(key=lambda combo: (sum(combo), combo), reverse=True)
    return found


def search_hitting_sets(colony: ringlife.Board):
    """Try the small product of per-line optimal hitting sets.

    A given line can need several overlapping birth windows covered by the same removal. Different optimal covers leave different cells alive, and those leftovers can interact at a corner on a later generation, so the full 20-generation check is what decides whether a cover is usable.
    """
    cols = colony.cols
    lines = threat_lines(colony)
    if not lines:
        return None

    per_line = ringlife.REMOVAL_LIMIT // len(lines)
    if per_line * len(lines) != ringlife.REMOVAL_LIMIT:
        return None

    candidates = []
    for line in lines:
        sets = hitting_sets(len(line), per_line)
        if not sets:
            return None
        candidates.append(sets)

    for combo in itertools.product(*candidates):
        cells = list(colony.cells)
        removed = set()
        for line, choice in zip(lines, combo):
            for offset in choice:
                row, col = line[offset]
                index = row * cols + col
                cells[index] = 0
                removed.add(index)

        generation, _ = ringlife.first_breach(cells, colony.cols, colony.rows)
        if generation is None:
            return cells, removed

    return None


def load_recorded_fallback(colony: ringlife.Board):
    """Recorded board from make_colony.py, used only if search stalls."""
    path = HERE / "removal.txt"
    if not path.exists():
        raise SystemExit("greedy search stalled and no recorded solution exists")
    board = ringlife.parse(path.read_text(encoding="utf-8"))
    removed = {
        i for i in range(len(colony.cells))
        if colony.cells[i] and not board.cells[i]
    }
    return list(board.cells), removed


def verify(colony: ringlife.Board, cells, removed) -> None:
    """Fail loudly unless this is a legal, contained removal set."""
    if len(removed) > ringlife.REMOVAL_LIMIT:
        raise SystemExit(
            f"solution removes {len(removed)} cells, over the "
            f"{ringlife.REMOVAL_LIMIT}-cell limit"
        )

    for index, value in enumerate(cells):
        if value and not colony.cells[index]:
            raise SystemExit(f"solution adds a live cell at index {index}")

    if not ringlife.is_contained(cells, colony.cols, colony.rows):
        raise SystemExit("solution is not contained at generation 0")

    generation, violations = ringlife.first_breach(cells, colony.cols, colony.rows)
    if generation is not None:
        raise SystemExit(
            f"solution breaches at generation {generation} "
            f"({len(violations)} cells in the exclusion border)"
        )


def submit(url: str, board_text: str) -> dict:
    request = urllib.request.Request(
        url.rstrip("/") + "/submit",
        data=board_text.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"server rejected the board (HTTP {exc.code}): {body}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:40818")
    args = parser.parse_args()

    colony_path = CHALLENGE / "dist" / "colony.txt"
    if not colony_path.exists():
        colony_path = CHALLENGE / "src" / "colony.txt"
    colony = ringlife.parse(colony_path.read_text(encoding="utf-8"))

    cells, removed = greedy_removals(colony)
    if ringlife.first_breach(cells, colony.cols, colony.rows)[0] is not None:
        found = search_hitting_sets(colony)
        if found is not None:
            cells, removed = found
        else:
            cells, removed = load_recorded_fallback(colony)

    verify(colony, cells, removed)

    board = ringlife.Board(colony.cols, colony.rows, 0, tuple(cells))
    board_text = ringlife.serialize(board)

    print(
        f"removed {len(removed)} cell(s); {board.alive()} alive; "
        f"contained for {ringlife.CONTAINMENT_GENERATIONS} generations"
    )

    result = submit(args.url, board_text)
    print(json.dumps(result, indent=2))

    if not result.get("flag"):
        raise SystemExit("no flag returned — the colony was not contained")


if __name__ == "__main__":
    main()
