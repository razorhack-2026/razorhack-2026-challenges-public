# Encrypted Telemetry -- solution (GM only)

Rogue Swarm tier 3. Technique: **unknown initial value scan, narrowed with
Changed / Unchanged, then a freeze**. Built with raylib 6.2 (rlsw CPU renderer).

## Why it can't be played straight

Same rigged game as Hull Breach: every 2.5 s a full-width curtain volley with
gaps narrower than the ship, so each volley is a guaranteed hit, plus aimed
shots and divers, against 80 drones over five waves. PD-1 gets 5 hull points
this time. Checked: sweeping + auto-fire with no edits loses all 5 inside 30 s
with 15 of 80 drones down.

The hull is never stored in the clear. Memory holds `hull ^ key`, where the key
is drawn once per process with `getrandom()` (libsodium) and its high half is
never zero. The HUD decodes it into a local for display. So:

- **An exact-value scan finds nothing.** Checked: 8 static slots equal 5 on the
  launch screen, and after hits none of them reads 4 or 3.
- **Decreased / Increased are unreliable.** XOR with a fixed key flips low bits,
  so the stored value goes up on some hits and down on others.
- **Writing a raw value fails.** A decoded hull above 9999 means the telemetry
  is garbage: the game ends the run with `HULL TELEMETRY INVALID / FIRE CONTROL
  LOCKED OUT` (the HUD shows `HULL ??`). Checked by writing `999` into the slot.

A damage log also changes on every hit and at no other time: a report sequence
number (jumps by 1-4), a hit count, the frame of the last hit, and the ship's x
at the last hit. These are the look-alikes that survive the scans with the
hull.

## Intended solve (Cheat Engine 7.7.1, Linux)

1. Run `./encrypted_telemetry` and leave it on the launch screen (HULL 5).
2. Cheat Engine → open process `encrypted_telemetry`. Value type **4 Bytes**,
   scan type **Unknown initial value** → **First Scan** (about 29M slots).
3. Press Space to launch, then **P** to pause whenever you want time. While
   nothing hits you, **Next Scan → Unchanged value** a couple of times.
4. Get hit (the HUD number drops), pause, **Next Scan → Changed value**. Unpause
   for half a second (PD-1 blinks: it can't be hit again for 1 s), pause,
   **Next Scan → Unchanged value**. Repeat two or three times.
5. Four green static `encrypted_telemetry+…` entries are left. Three are small
   and obviously counters (sequence, hit count, a frame number in the
   thousands). The fourth is a large number that has nothing to do with the HUD:
   that is the encrypted hull.
6. Add it to the address list and tick **Active** to freeze it. Hits still land
   but Cheat Engine writes the old value back, so the HUD stays put. Freezing
   the look-alikes does nothing (the HUD keeps dropping), which is how a player
   tells them apart.
7. Unpause and shoot down all 80 drones. The command link key prints on screen
   and to stdout: `COMMAND LINK KEY: flag{...}`.

Don't freeze at HULL 1: a hit takes it to 0 and the run ends in the same frame,
before Cheat Engine re-writes it. Freeze at 2 or more, or write back the value
from the **First** column (the stored form of 5).

If the run dies first, press R. The key is drawn once per process, so the
relaunch stores 5 the same way and the scan carries on.

**Accepted alternates.**
- **Decode it.** The stored value and the HUD give the key:
  `key = stored ^ shown`. Write `999 ^ key` and the hull reads 999.
- **Freeze all four survivors.** Faster than testing them one by one; the
  look-alikes are harmless to freeze.
- **Freeze the invulnerability timer** (PD-1's `int32` after the hull, counts
  60 → 0 after each hit). It changes between hits, so the intended scans drop
  it, but a player who finds it gets a ship that can't be hit (follows from
  the code; not run).
- Reversing the shard derivation (`rs_secret`) and decrypting offline. Harder
  than the intended solve.

**Checked with Cheat Engine 7.7.1 Linux on Kali 2026.2 (2026-11-04).** CE
attached to `encrypted_telemetry` from its process list. Unknown initial value
(4 Bytes): 29,264,896. Two Unchanged scans before any hit: 29,228,976. One hit
(HULL 4) and Changed: 13,198. Two more rounds of hit → Changed, idle 0.5 s →
Unchanged: **4**, exactly the hull and the three counters (the last-hit x
dropped out because the ship sat still between hits). With the hull frozen at
HULL 2, the hit count went from 3 to 25 while the HUD stayed at 2, and clearing
all 80 drones printed the key, which matches `challenge.yml`. **The trial
allows Changed/Unchanged scans and freezing.**

**Cheat Engine 7.7.1 trial mode.** Same as Hull Breach: the "Patreon or Trial"
dialog at start, and scans stop after about 1.5 h of CE running. Restart CE and
reattach; the game keeps its state.

Equivalent free tools on Kali: `scanmem` (`option scan_data_type int32`,
`snapshot`, then `!=` after a hit and `=` between hits, then `set` in a loop),
PINCE (has freezing), or GameConqueror. Not run against this tier.

## Scripted reference solve

`make verify` runs `solve.py` under Xvfb. It snapshots every aligned 4-byte
slot in the game module's static memory, drops everything that changes in the
hit-free first 2.5 s, then sits still without firing and samples at 20 Hz until
7.5 s. It keeps slots that changed in a few separate samples, never in two in a
row, and never back to an earlier value (an enemy bullet's slot goes
0 → live → 0), and takes the largest group that changed in exactly the same
samples: the hits. That group is the hull plus the damage-log counters. It
freezes all of them at their first-scan values (the hull's is 5), relaunches
with R if PD-1 was lost meanwhile, and flies with auto-fire until the key
prints. Passed 3/3 on `ctf-attack` (57-72 s per run).

The game is a child of the solver, so Yama `ptrace_scope` 1 allows it. A
separate Cheat Engine process needs root or `CAP_SYS_PTRACE`.

## Anti-bypass

Same scheme as Hull Breach, with a new per-tier secret. No flag string is in
the binary. Each drone's 16-byte shard (SHA-256 of the per-tier secret, the tier
and the drone ID) is XORed into an accumulator only when that drone is shot
down. When all 80 are down, SHA-256(accumulator ‖ "RS-T" ‖ tier) opens a
ChaCha20-Poly1305 ciphertext (libsodium, statically linked).

- Checked: with the hull frozen, setting the kill counter to 79 and shooting
  one more drone reaches the win screen but prints `COMMAND CODE CORRUPTED`.
- Accepted alternate: reverse the shard derivation and decrypt offline.

## Display performance (GM note)

Same as Hull Breach: logic at a fixed 60 Hz, drawing at 30 FPS by default,
`RS_FPS=15..60` to tune it for a slow remote desktop.
