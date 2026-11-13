# Hull Breach

**Category:** Reverse Engineering
**Difficulty:** Easy
**Author:** Andy Roid

## Description

The swarm hit us before PD-1 even cleared the launch rail. Fire control says
the point-defense drone's hull integrity was drained to 3 while it sat in the
bay -- someone got into its software first. Eighty hostile drones are inbound,
and they fly in curtains you can't dodge.

Every drone you shoot down drops a fragment of the swarm's command-link key.
Bring down all eighty and the key reassembles. Three hull points will not get
you there. Fire control is your console now: it's your ship, so override
whatever you need to.

Run `hull_breach` on your Kali box (it needs an X display). The game runs
locally; nothing to connect to.

## Files Provided

- `hull_breach` -- the PD-1 fire-control game (Linux x86-64)
- `SHA256SUMS` -- checksum of the file above

## Controls

Arrows or A/D to move, Space to fire, P to pause, R to relaunch after a loss.

## Requirements

Linux x86-64 with an X display; no GPU needed. Runtime libraries: glibc 2.35+,
libX11, libXext, libXrandr, libXcursor, libXi and libGL (Debian/Kali packages
`libx11-6 libxext6 libxrandr2 libxcursor1 libxi6 libgl1`). A standard Kali
desktop install already has them.
