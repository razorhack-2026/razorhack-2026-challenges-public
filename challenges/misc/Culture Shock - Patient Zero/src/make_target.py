"""Generate the challenge target board from a deterministic seed.

GM-only tool. It writes two files:

  src/target.txt      -- the target the server compares against (never ships)
  solution/seed.txt   -- the predecessor seed, used by the reference solution

Re-running this script reproduces the exact same pair, so the challenge stays
solvable if the target ever needs rebuilding.

    python3 src/make_target.py [--cols 12] [--rows 12] [--generations 3]
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import ringlife

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE.parent

# Fixed seed so the target is reproducible.
RNG_SEED = 20261106
DENSITY = 0.1


def build_seed(cols: int, rows: int) -> ringlife.Board:
    rng = random.Random(RNG_SEED)
    cells = tuple(1 if rng.random() < DENSITY else 0 for _ in range(cols * rows))
    return ringlife.Board(cols=cols, rows=rows, generation=0, cells=cells)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cols", type=int, default=12)
    parser.add_argument("--rows", type=int, default=12)
    parser.add_argument("--generations", type=int, default=3)
    args = parser.parse_args()

    seed = build_seed(args.cols, args.rows)
    target = ringlife.evolve(seed, args.generations)

    if target.alive() == 0:
        raise SystemExit("target died out — pick a different RNG seed or density")

    (HERE / "target.txt").write_text(ringlife.serialize(target), encoding="utf-8")
    (CHALLENGE / "solution").mkdir(exist_ok=True)
    (CHALLENGE / "solution" / "seed.txt").write_text(
        ringlife.serialize(seed), encoding="utf-8"
    )

    print(
        f"seed: {seed.alive()} alive -> target: {target.alive()} alive "
        f"after {args.generations} generations ({args.cols}x{args.rows})"
    )


if __name__ == "__main__":
    main()
