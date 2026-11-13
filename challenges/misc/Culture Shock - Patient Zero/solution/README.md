# Solution — Culture Shock - Patient Zero

**Flag:** `flag{it's_alive!!!1!}`

## What the challenge is

The player is handed `target.txt`: a **12×12** snapshot of the colony at generation 3. They must
find a starting board (generation 0) that, when evolved **3 generations** under B3/S23 with a
*radius-2 neighbor ring*, reproduces that snapshot exactly. Boards are compared on dimensions and
cells only — the `generation:` field in a submission is ignored.

The rule differs from ordinary Life in the neighborhood. A cell's neighbors are the 16 cells at
Chebyshev distance **exactly 2**:

```
. . X X X . .        X = neighbor
. . X . X . .        (the inner 3x3, including the 8 directly
. X . O . X .         adjacent cells, is NOT counted)
. . X . X . .
. . X X X . .
```

Cells outside the grid are permanently dead (hard walls, no torus wrapping). This is the single
most common way to get a "correct-looking" answer that still fails: wrapping the edges changes
the evolution completely.

## Solving it

1. **Read the rule out of the page.** `src/index.html` (served at the challenge address) ships
   the whole engine in plain JavaScript: `ringOffsets()`, `countneighbors()`, `step()`, plus the
   exported plain-text board format. Nothing is minified or hidden — the difficulty is the
   reverse problem, not the rule.
2. **Confirm the target.** `GET /target` (or `dist/target.txt`) gives the goal board. The 12×12
   submission size is enforced, which tells you the board dimensions the seed must have.
3. **Solve the reverse problem.** Forward evolution is deterministic, so any candidate seed can
   be checked cheaply. Three practical approaches:
   - **Unroll and hand it to a SAT/SMT solver (what the reference does).** Give every cell one
     Boolean per generation. For each cell, sum its 16 radius-2 neighbors and assert the B3/S23
     rule (`next ⇔ neighbors == 3 ∨ (alive ∧ neighbors == 2)`); assert that generation 3 equals
     the target and let the solver find generation 0. Cardinality constraints (`PbEq` in z3, or a
     cardinality encoding in PySAT) keep the model exact. On a 12×12 board this solves in a few
     seconds.
   - **Local search / hill climbing:** score a candidate by how many cells of its 3rd generation
     differ from the target, then flip a few cells and keep improvements. The rule is chaotic, so
     restarts matter more than clever moves. Works for shallow searches but is unreliable here.
   - **Reverse row search:** a target cell depends on cells two rows/columns away, so you can
     enumerate candidate rows from the top and prune partial boards that already contradict the
     target. This is the deterministic alternative to SAT.

   Because the forward map is many-to-one, many different gen-0 boards reach the same target —
   you only need one.
4. **Submit.** POST the board to `/submit` in the same plain-text format the page exports:

```bash
curl -s -X POST --data-binary @candidate.txt \
     -H 'Content-Type: text/plain' http://<host>:40817/submit
```

or just draw it in the editor and press **Submit**. A match returns the flag; anything else
returns the generation-3 population versus the target's so you can tell how close you were.

## Reference solution

`solution/solve.py` models the reverse problem directly with **z3**: it unrolls the automaton for
3 generations over 12×12 Boolean variables, encodes every cell update with pseudo-Boolean
cardinality constraints, asserts that generation 3 equals `dist/target.txt`, and lets z3 recover
generation 0. It reads **only the competitor handout** (`dist/target.txt`) plus the shared rule
engine (`src/ringlife.py`) — never `solution/seed.txt` or `src/target.txt` — then verifies the
seed locally and POSTs it.

```bash
pip install -r solution/requirements.txt   # z3-solver
python3 solution/solve.py --url http://localhost:40817
```

It prints the recovered seed, a local verification line, and the flag.

`solution/seed.txt` is the **recorded generator seed** (16 live cells), kept so the challenge can
be rebuilt deterministically. `solve.py` does not use it and normally finds a *different* valid
seed (for example 43 live cells) — that is expected, because the forward map is many-to-one.

## Regenerating the pair

```bash
python3 src/make_target.py            # deterministic: 12x12, 3 generations, RNG_SEED = 20261106, density 0.1
cp src/target.txt dist/target.txt     # refresh the competitor handout
```

`make_target.py` writes both `src/target.txt` (the answer key, never shipped) and
`solution/seed.txt` (the recorded seed). If you change `RING_RADIUS`, `WRAP`, the board size, or
`GENERATIONS`, regenerate — and keep `GENERATIONS` in sync across `src/app.py` and
`solution/solve.py`. Note that 3 generations on a 34×34 board is far harder than 12×12; the board
was deliberately shrunk so the reverse search stays tractable for competitors.
