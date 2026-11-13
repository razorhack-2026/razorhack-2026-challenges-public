# Culture Shock - Patient Zero

**Category:** Misc
**Difficulty:** Medium
**Author:** Lt. Niko Copernicus

## Description (what the competitor will see)

Our biologists recently discovered a strain of exobacteria living in the core of a large nearby asteroid! The colony seems to grow in a chaotic but predictable manner, almost like it's playing a game of life... While trying to study the exobacterium, an intern was supposed to record the colony's size and shape at each generation. Unfortunately, they fell asleep at their desk overnight and were only able to capture the generation available in `target.txt`. We don't have the resources to perform the experiment again, but the biologists did figure out the rules by which the colony changes between each generation.

At each new generation, each cell is born, dies, or survives depending on the state of its neighbors in a ring of cells with Chebyshev distance exactly 2, excluding the 8 cells directly adjacent. A new cell is born in an empty grid space if it has exactly 3 live neighbors, and a live cell survives if it has exactly 2 or 3 live neighbors. Live cells with less than 2 or more than 3 neighbors are unable to obtain the resources it needs to survive by under- or overpopulation and dies in the next generation. Cells outside the recorded grid are always dead.

You need to reconstruct the colony as it looked exactly **3 generations before** the captured snapshot. The biologists have provided a simple web page at `http://<host>:40817` to submit your proposal for the seed state. The proposal will then be simulated for 3 generations to verify that it reaches the target state.

## Files provided

- `target.txt` - the captured colony snapshot (the state your colony must reach)

## Connecting

The board editor and the submission service are served together at `http://<host>:40817`. Draw a starting colony on the grid, then press
**Submit**; the target snapshot is rendered underneath for reference.
