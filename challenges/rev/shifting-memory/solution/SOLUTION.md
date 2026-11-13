# Shifting Memory -- solution (GM only)

Rogue Swarm tier 4. Technique: **pointer scan, then freeze through the
pointer**. Built with raylib 6.2 (rlsw CPU renderer).

## Why it can't be played straight

Same rigged game as Hull Breach: every 2.5 s a full-width curtain volley with
gaps narrower than the ship, so each volley is a guaranteed hit, plus aimed
shots and divers, against 80 drones over five waves. PD-1 has 5 hull points.
Checked: sweeping + auto-fire with no edits is lost at BANK 05 (about 15 s)
with 32 of 80 drones down.

The hull is a plain `int32`, but it lives in a heap-allocated player struct
reached only through the global `g_player` (`.bss`, a fixed offset from the
module base under PIE). Every 3 s of game time (180 frames; pausing stops the
clock) the game allocates a new struct, copies the old one, **clamps the hull to
5**, bumps the BANK number on the HUD, and retires the old struct. Retired
structs stay allocated for 6 moves and keep their last values, then are freed,
so glibc hands their chunks back later and the address cycles. So:

- **A one-time write lasts until the next move.** Checked: writing 999 held
  until the move, then the live copy read 5; the old address kept counting
  down (997) as a retired copy.
- **Freezing the found address doesn't hold.** Checked: freezing 999 at the
  address found after the first hit, PD-1 was lost at BANK 06 with 31 drones
  down, no better than honest play. (When glibc later hands that chunk back
  the freeze would help for one bank, but the run is long over by then.)
- **The launch-screen scan goes stale before the first hit.** The first move
  (BANK 01, 3 s) lands before the first hit (about 3.5 s), so "Exact 5, take a
  hit, Next Scan 4" on the launch-screen list finds nothing. Checked with
  Cheat Engine: 3,356 → 0.

## Intended solve (Cheat Engine 7.7.1, Linux)

1. Run `./shifting_memory`, open it in Cheat Engine, launch with Space. **P**
   pauses, and pausing stops the moves too.
2. Find the hull **within one bank**: after a hit, pause, New Scan, 4 Bytes
   Exact Value = the HUD number. Take another hit before BANK changes, pause,
   Next Scan the new number. One heap address is left (black, not green).
3. Add it to the address list, right-click → **Pointer scan for this
   address**. Max level 1–2 is plenty (the default 7 should also work, with more
   paths to sort through; not run). Save the `.PTR` file anywhere. Result: one path,
   `"shifting_memory"+…` with offset **14**.
4. Optional check: unpause until BANK changes. The pointer entry follows the
   hull to its new address; the plain entry is left on a stale copy. (With a
   deeper scan, Pointer scanner → Rescan memory after a move should filter out
   paths that broke; not run.)
5. Double-click the path into the address list, set it to `999`, tick
   **Active**. The clamp knocks it back to 5 at each move, and Cheat Engine
   writes 999 again within its freeze interval.
6. Unpause and shoot down all 80 drones. The command link key prints on screen
   and to stdout: `COMMAND LINK KEY: flag{...}`.

**Accepted alternates.**
- **Find the pointer by hand:** 8 Bytes, Value between `addr - 0x100` and
  `addr` (hex), in the module's static memory (green) gives `g_player`; the
  offset is the difference.
- **Re-find and rewrite after every move.** It works but needs a fresh scan
  every 3 s of play; pausing makes it possible, just slow.
- "Find out what writes to this address" (debugger) should show the
  `+14` access and lead back to the base. That is tier 5's tool; fine if it
  works (not run).
- Reversing the shard derivation (`rs_secret`) and decrypting offline.

**Checked with Cheat Engine 7.7.1 Linux on Kali 2026.2 (2026-11-04).** Exact
Value 5 on the launch screen: 3,356. After the first hit (HULL 4, BANK 01),
Next Scan 4: **0**, the move had already happened. New Scan 4, one more hit in
the same bank, Next Scan 3: **1** (a heap address). Pointer scan (max level 2,
other defaults): **1 path**, `"shifting_memory"+…` offset 14. Set to 999 and
frozen, the HUD read HULL 999 through BANK 17, with the pointer entry moving to
new addresses (and back to an earlier chunk once glibc reused it), and
clearing all 80 drones printed the key, which matches `challenge.yml`. **The
trial allows the pointer scanner and pointer freezing.**

**Cheat Engine 7.7.1 trial mode.** Same as Hull Breach: the "Patreon or Trial"
dialog at start, and scans stop after about 1.5 h of CE running. Restart CE and
reattach; the game keeps its state. The pointer scan's `.PTR` file outlives a
restart.

Equivalent free tools on Kali: PINCE has a pointer scanner; `scanmem` has none,
so there the by-hand pointer search is the way. Not run against this tier.

## Scripted reference solve

`make verify` runs `solve.py` under Xvfb. It sits still and watches every
aligned `int32` on `[heap]` with a value 1–5 at 20 Hz; when one drops by exactly
1 (a hit), it looks in the module's static memory for an 8-byte slot holding an
address up to 0x100 below it (pointer scan, level 1). It keeps the pointer whose
value changes at the next move and still leads to a hull of 0–5, freezes 999
through it (re-read the pointer, write the hull, every 20 ms), and flies with
auto-fire in full wall-to-wall passes until the key prints. Passed 5/5 on
`ctf-attack` (47–58 s per run).

Keep the full passes. With 1.1 s sweeps the ship drifts into the band the left
wall clamps it to and can strand the last drone at the far right; that failed
1 run in 3 before the change.

The game is a child of the solver, so Yama `ptrace_scope` 1 allows it. A
separate Cheat Engine process needs root or `CAP_SYS_PTRACE`.

## Anti-bypass

Same scheme as Hull Breach, with a new per-tier secret. No flag string is in
the binary. Each drone's 16-byte shard (SHA-256 of the per-tier secret, the tier
and the drone ID) is XORed into an accumulator only when that drone is shot
down. When all 80 are down, SHA-256(accumulator ‖ "RS-T" ‖ tier) opens a
ChaCha20-Poly1305 ciphertext (libsodium, statically linked).

- Checked: with the hull frozen through the pointer, setting the kill counter
  to 79 and shooting one more drone prints `COMMAND CODE CORRUPTED`.
- Accepted alternate: reverse the shard derivation and decrypt offline.

## Display performance (GM note)

Same as Hull Breach: logic at a fixed 60 Hz, drawing at 30 FPS by default,
`RS_FPS=15..60` to tune it for a slow remote desktop.
