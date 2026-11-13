# Blind Pilot — GM Solution

The field simulation is deterministic between scans, but only adjacent cells are visible at any moment. The reference pilot accumulates observations and predicts asteroid motion, including edge bounces.

1. Scan all in-bounds neighboring cells and record each asteroid's position and heading.
2. Advance the known asteroid map by one tick after every move.
3. Search short movement sequences, avoiding predicted collisions and preferring progress toward the jump gate.
4. Repeat scans and planning until the ship reaches the gate. Each new connection gets a fresh field.

`solve.py` implements the pilot. `test_challenge.py` covers boundary motion, radar results, collision damage, scan parsing, and valid move selection.
