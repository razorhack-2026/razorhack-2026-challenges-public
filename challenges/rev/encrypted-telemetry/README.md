# Encrypted Telemetry

**Category:** Reverse Engineering
**Difficulty:** Medium
**Author:** Andy Roid

## Description

The swarm is back, eighty drones flying curtains you can't dodge, and the
saboteur got into PD-1's software again. Fire control gave the hull back its
five points, but the hull telemetry is encrypted now. The HUD still decodes it
and shows the right number. Nothing else on board does.

Every drone you shoot down drops a fragment of the swarm's command-link key.
Bring down all eighty and the key reassembles. Five hull points will not get
you there. Fire control is your console: it's your ship, so override whatever
you need to.

Run `encrypted_telemetry` on your Kali box (it needs an X display). The game
runs locally; nothing to connect to.

## Files Provided

- `encrypted_telemetry` -- the PD-1 fire-control game (Linux x86-64)
- `SHA256SUMS` -- checksum of the file above

## Controls

Arrows or A/D to move, Space to fire, P to pause, R to relaunch after a loss.
