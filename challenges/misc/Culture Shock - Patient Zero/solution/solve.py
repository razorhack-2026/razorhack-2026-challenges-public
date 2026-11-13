"""Reference solution for Culture Shock: Patient Zero.

A competitor is handed only ``dist/target.txt``: a snapshot of the colony at
some generation.  The task is to recover a board that, after the colony's rules
are applied for GENERATIONS steps (B3/S23, neighbor ring of radius 2, hard board
edges), reproduces that snapshot exactly.

Forward evolution is a local, deterministic rule, so the reverse problem is a
constraint-satisfaction problem.  This solver does what the challenge hints
point at: it unrolls the automaton for GENERATIONS with z3 Boolean variables
(one layer per generation) and asks z3 for a generation-0 assignment whose
GENERATIONS-th generation equals the target.  Each cell update is encoded with
two pseudo-Boolean cardinality constraints (``PbEq``), so the model is exact.

    python3 solution/solve.py [--url http://localhost:40817]

Requires z3-solver (see solution/requirements.txt):

    pip install -r solution/requirements.txt

The solver reads only the competitor handout ``dist/target.txt`` and the shared
rule engine in ``src/ringlife.py`` — never ``solution/seed.txt`` or
``src/target.txt``.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import z3
except ImportError:  # pragma: no cover - dependency hint
    raise SystemExit(
        "solution/solve.py needs z3-solver; install it with:\n"
        "    pip install -r solution/requirements.txt"
    )

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent
sys.path.insert(0, str(CHALLENGE / "src"))

import ringlife  # noqa: E402

# Keep in sync with src/app.py and the `generation:` header of dist/target.txt.
GENERATIONS = 3


def neighbour_indices(cols: int, rows: int):
    """For every cell, the indices of its radius-2 ring neighbours."""
    ring = ringlife.ring_offsets()
    indices = []
    for index in range(cols * rows):
        row, col = divmod(index, cols)
        indices.append(
            [
                (row + dy) * cols + (col + dx)
                for dx, dy in ring
                if 0 <= row + dy < rows and 0 <= col + dx < cols
            ]
        )
    return indices


def solve_seed(target: ringlife.Board, generations: int = GENERATIONS) -> ringlife.Board:
    """Find a board that reaches ``target`` in ``generations`` generations."""
    cols, rows = target.cols, target.rows
    n = cols * rows
    neighbours = neighbour_indices(cols, rows)

    solver = z3.SolverFor("QF_FD")
    solver.set(timeout=5 * 60 * 1000)  # 5 minutes; a real solve takes seconds

    # One free Boolean per cell per generation; layer 0 is the seed we solve for.
    layers = [
        [z3.Bool(f"g{g}_{i}") for i in range(n)] for g in range(generations + 1)
    ]

    for g in range(1, generations + 1):
        prev, cur = layers[g - 1], layers[g]
        for i in range(n):
            ring = [(prev[j], 1) for j in neighbours[i]]
            # B3/S23: born on exactly 3 neighbours, or survives with 2 or 3.
            born = z3.PbEq(ring, 3)
            survives = z3.And(prev[i], z3.PbEq(ring, 2))
            solver.add(cur[i] == z3.Or(born, survives))

    for i in range(n):
        solver.add(layers[generations][i] == bool(target.cells[i]))

    print(
        f"solving {cols}x{rows} board {generations} generations back with z3...",
        file=sys.stderr,
    )
    result = solver.check()
    if result != z3.sat:
        raise SystemExit(f"could not find a predecessor (z3 returned {result})")

    model = solver.model()
    cells = [
        1 if z3.is_true(model.eval(layers[0][i], model_completion=True)) else 0
        for i in range(n)
    ]
    return ringlife.Board(cols, rows, 0, tuple(cells))


def verify(target: ringlife.Board, seed: ringlife.Board, generations: int = GENERATIONS) -> None:
    """Fail loudly if the recovered seed does not reproduce the target."""
    final = ringlife.evolve(seed, generations)
    if not ringlife.same_board(final, target):
        raise SystemExit("internal error: recovered seed does not reach the target")
    print(
        f"verified: {seed.alive()} live cells -> {final.alive()} live cells "
        f"after {generations} generations",
        file=sys.stderr,
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
    except urllib.error.URLError as exc:
        raise SystemExit(f"could not reach {url}: {exc.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:40817")
    args = parser.parse_args()

    target_path = CHALLENGE / "dist" / "target.txt"
    target = ringlife.parse(target_path.read_text(encoding="utf-8"))
    if target.generation and target.generation != GENERATIONS:
        raise SystemExit(
            f"dist/target.txt is at generation {target.generation} but this solver "
            f"is configured for {GENERATIONS}; update GENERATIONS"
        )

    seed = solve_seed(target)
    verify(target, seed)

    board_text = ringlife.serialize(seed)
    print(board_text, end="")

    result = submit(args.url, board_text)
    print(json.dumps(result, indent=2))
    if not result.get("flag"):
        raise SystemExit("no flag returned — board did not match the target")


if __name__ == "__main__":
    main()
