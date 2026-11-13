# Culture Shock: Adapt or Die

**Category:** Misc
**Difficulty:** Hard
**Author:** Lt. Niko Copernicus

## Description

The biologists performed an experiment to test how the exobacterium's environment affects it by exposing a colony to intense radiation. The colony survived, but it seems to have mutated! The colony's growth has strayed from simulation, so its growth rules must have changed.

The biologists need the growth rule correction published before the next containment cycle. Build a culture on the probe board and ask the ship's imaging rig to run it forward one generation at a time; each observation costs a dose of reagent, and the doses are limited. The archive also holds a handful of cultures whose transitions have been pre-recorded which you can study for free. When you are confident, submit the notation that describes the new growth law — `B<birth counts>/S<survival counts>` over the same radius-2 ring the earlier survey used.

## Files provided

- `specimen.txt` - the culture recovered from the reactor, in the same plain-text board format the lab uses

## Connecting

The probe lab, the archive and the submission service are served together at `http://<host>:40819`. Import `specimen.txt`, build probe cultures on the grid, watch the archived cultures, then submit the corrected growth law.
