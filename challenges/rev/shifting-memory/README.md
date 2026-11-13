# Shifting Memory

**Category:** Reverse Engineering
**Difficulty:** Medium
**Author:** Andy Roid

## Description

The saboteur is still in PD-1's fire control, and now its memory banks won't
sit still. Every few seconds the fire-control software packs the drone's state
up and moves it somewhere new, and on the way it trims the hull back to
regulation. Whatever you fix stays fixed for a moment, and then it's somewhere
else.

Eighty drones are inbound in curtains you can't dodge. Every drone you shoot
down drops a fragment of the swarm's command-link key; bring down all eighty
and the key reassembles. Five hull points will not get you there. Fire control
is your console: it's your ship, so override whatever you need to.

Run `shifting_memory` on your Kali box (it needs an X display). The game runs
locally; nothing to connect to.

## Files Provided

- `shifting_memory` -- the PD-1 fire-control game (Linux x86-64)
- `SHA256SUMS` -- checksum of the file above

## Controls

Arrows or A/D to move, Space to fire, P to pause, R to relaunch after a loss.
