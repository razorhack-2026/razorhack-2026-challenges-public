# Scoring & Difficulty Guide

Tuned for an **intermediate (undergraduate)** field. Point values assume a
CTFd-style board; adjust to your event's scale. Total: **1000 points** across
seven flags, weighted by effort and by how many earlier objectives each one
depends on.

| # | Flag | Category | Difficulty | Points | Depends on |
|---|------|----------|------------|--------|------------|
| 1 | Hailing frequencies | ICS / recon | easy | 75 | - |
| 2 | The ghost deck | web / HMI | easy | 100 | - |
| 3 | Breathe easy (O2) | ICS / control | medium | 125 | 1 |
| 4 | Scrub it out (CO2) | ICS / control | medium | 150 | 1 |
| 5 | Goldilocks (temp) | ICS / control | medium | 125 | 1 |
| 6 | Exorcise MaintSync | ICS + web | hard | 200 | 2, 3-5 |
| 7 | All systems nominal | ICS / capstone | hard | 225 | 6 |

Suggested **first-blood** bonus: +10% of the flag's value to the first team.

## Difficulty curve

1-2 are on-ramps: pure read/recon, no process understanding, solvable in the
first 15 minutes so every team gets on the board. 3-5 teach the
read-modify-write loop and the idea that a setpoint can be driven - but they're
deliberately *transient* (MaintSync reverts them) which pushes teams toward the
real root cause. 6 is the pivot: it links the HMI (where the code lives) to the
PLC (where it's written) and rewards teams who explored the gateway in
challenge 2. 7 gates on all prior work plus a 30-second stable hold, so it's a
natural closer rather than a grind.

## Dynamic scoring note

If your platform uses decay (points drop as more teams solve), leave 1-2 on a
gentle curve and 6-7 on a steeper one - they're the differentiators. The three
control flags (3-5) are independent enough that teams can split them across
members, which is good for team play; keep their values close so there's no
"correct" order.

## Timing the hints

- Release **nudge** tier at T+30 min, **bigger** at T+90 min.
- Keep **near-spoiler** behind a point cost (e.g. -25% of flag value) rather
  than a timer, so it stays a real last resort.
- Hints and tiers are in `HINTS.md`.

## Pre-event checklist

1. `docker compose run --rm builder` with event-specific flags in `flags.json`
   (it also runs the PLC unit tests - all must pass).
2. Build and push the images, and start team 00's copy (`../README.md`).
3. `python3 solution/eclss/solve.py --host <host> --port 502` -> expect all six
   Modbus flags and "rig is healthy."
4. Browse `/crew-manifest` (flag 2) and `/maint` (the code only, no flag).
5. Stop and Start the copy: every start is a fresh ship.
