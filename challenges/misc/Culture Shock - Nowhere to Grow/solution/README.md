# Solution — Culture Shock - Nowhere to Grow

**Flag:** `flag{and_stay_there!}`

## What the challenge is

The player gets `dist/colony.txt`: a 34×34 colony that is contained at generation 0 (no live cells in the two outermost rows/columns on any side). Under B3/S23 with a *radius-2 neighbor ring* it breaches that border on generation 1.

They must submit a board that:

- keeps the same dimensions,
- only removes live cells from the given colony (no additions),
- removes at most 16 live cells,
- stays contained for generations 0 through 20.

## The rule

A cell's neighbors are the 16 cells at Chebyshev distance **exactly 2**:

```
. X X X X X .        X = neighbor
. X . . . X .        (the inner 3x3, including the 8 directly
. X . O . X .         adjacent cells, is NOT counted)
. X . . . X .
. X X X X X .
```

Cells outside the grid are permanently dead (hard walls, no torus wrapping). Wrapping the edges changes the evolution completely and will not help.

## Solving it

1. **Read the rule out of the page.** `src/index.html` (served at the challenge address) ships the whole engine in plain JavaScript: `ringOffsets()`, `countneighbors()`, `step()`, plus the exported plain-text board format.
2. **Find the generation-1 border births.** For each live cell in the exclusion border at generation 1, its radius-2 ring had exactly 3 live gen-0 neighbors. Removing any one of those neighbors stops that birth.
3. **Cover overlapping windows.** Each side of the colony is a 13-cell line spaced two apart. That line has 11 overlapping birth windows, and one removal can cancel up to three adjacent windows. Each side therefore needs at least 4 removals; 4 sides x 4 = 16, exactly the budget.
4. **Re-check the whole run.** Not every optimal 4-removal cover is usable: different covers leave different cells behind, and leftovers from adjacent sides can combine at a corner on a later generation. Verify the edited board for all 20 generations (the service does this too).
5. **Submit.** POST the edited board in the exported plain-text format:

```bash
curl -s -X POST --data-binary @candidate.txt \
     -H 'Content-Type: text/plain' http://<host>:40818/submit
```

## Reference solution

`solution/removal.txt` is the contained board to submit (100 live cells; 16 removed). `solution/removals.txt` lists the removed cells as 0-based `row,column` pairs.

`solution/solve.py` derives the removals from `dist/colony.txt` directly:

1. It finds the live cells on each innermost safe boundary line.
2. It enumerates every 4-cell set that hits all 11 consecutive-triple birth windows on each line (there are only five such sets per side), preferring spread-out covers.
3. It tests the 625 combinations across the four sides against the full 20-generation containment check and returns the first that holds.

The earlier simple greedy is still tried first; on this instance it can leave a corner pair that breaches at generation 7, which is exactly the extra wrinkle this version adds.

```bash
# against a running instance
python3 solution/solve.py --url http://localhost:40818
```

## Regenerating the pair

```bash
python3 src/make_colony.py            # deterministic construction + self-checks
```

This rewrites `src/colony.txt`, `dist/colony.txt`, `solution/removal.txt`, and `solution/removals.txt`. Keep `REMOVAL_LIMIT`, `CONTAINMENT_GENERATIONS`, and `CONTAINMENT_MARGIN` in `src/ringlife.py` in sync with the description if you change the challenge parameters.
