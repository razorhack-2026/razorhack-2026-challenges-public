# Hull Breach -- solution (GM only)

Rogue Swarm tier 1. Technique: **exact-value scan and write**. Built with raylib 6.2 (rlsw CPU renderer).

## Why it can't be played straight

PD-1 launches with 3 hull points. Every 2.5 s the swarm fires a curtain volley:
a full-width row of bullets 20 px apart, while the ship is 28 px wide, so no
position dodges it. Each volley is a guaranteed hit (the 1 s invulnerability
window is shorter than the volley period). Three hits end the run in about
10 s; clearing 80 drones over five waves takes well over a minute even with
perfect aim. Checked on the raylib build: sweeping + auto-fire with no edits
dies in 8-10 s with 11-15 kills across runs.

## Intended solve (Cheat Engine 7.7.1, Linux)

1. Run `./hull_breach`, leave it on the launch screen (HULL 3).
2. Cheat Engine → open process `hull_breach`. Value type **4 Bytes**, scan type
   **Exact Value**, value `3` → **First Scan** (about 4,000 hits: raylib's CPU
   renderer keeps large framebuffers full of small numbers).
3. Press Space to launch, take one hit (HULL 2). Press **P** to pause if you
   want time. **Next Scan** with value `2`, then again at HULL 1 if needed. The
   hull is the green static entry `hull_breach+16CCC0` (offset for this build).
4. Double-click it into the address list, set the value to `999` (or tick
   Active to freeze it).
5. Unpause and shoot down all 80 drones. The command link key prints on screen
   and to stdout: `COMMAND LINK KEY: flag{...}`.

If the run dies before the edit, keep scanning across it: HULL 0 → Next Scan
`0`, press R (HULL 3) → Next Scan `3`. The hull lives in a global, so the
address stays the same for the life of the process. Checked on `ctf-attack`
2026-11-03: scanning for 1 gave 46,257 hits, then 0 → 25, then 3 → 1.

Avoid writing to non-green matches. Some library counters elsewhere in the
process also count 3 → 2 → 1 now and then, and writing to them crashed the
game in testing.

**Cheat Engine 7.7.1 trial mode.** Without a Patreon login, CE starts with a
"Patreon or Trial" dialog (click the numbered button it names). The trial is
**time-limited**: after a while (about 1.5 h in testing, not measured exactly)
scans fail with "Trial time for this function has ended. Restart CE or become a
patreon". Restarting CE resets it; the game keeps running, so reattach and scan
again.

Equivalent free tools on Kali: `scanmem` (`pid`, `3`, take a hit, `2`,
`set 999`), PINCE, or GameConqueror.

## Scripted reference solve

`make verify` runs `solve.py` under Xvfb. It does the same scan → hit → rescan
→ write over `/proc/<pid>/mem`, then holds fire and sweeps until the key prints,
and compares it to the flag in `challenge.yml`. The game is a child of the
solver, so Yama `ptrace_scope` 1 allows it. A separate Cheat Engine process
needs root or `CAP_SYS_PTRACE`.

## Anti-bypass

No flag string is in the binary. Each drone's 16-byte shard (SHA-256 of a
per-tier secret, the tier and the drone ID) is XORed into an accumulator only
when the drone is shot down. When all 80 are down, SHA-256(accumulator ‖ "RS-T"
‖ tier) opens a ChaCha20-Poly1305 ciphertext (libsodium, statically linked).

- Checked: setting the kill counter to 79 and shooting one drone reaches the
  win screen but prints `COMMAND CODE CORRUPTED` (the AEAD tag fails).
- Accepted alternate: reverse the shard derivation (two 32-byte tables + an LCG
  in `rs_secret`), recompute the 80 shards and decrypt offline. That is harder
  than the intended solve and fine at this tier.

## Display performance (GM note)

The game logic runs at a fixed 60 Hz, and drawing runs at 30 FPS by default.
raylib's CPU renderer rewrites the whole window on every frame, so a remote
desktop (VNC/RDP, the Proxmox console, the Fargate desktop) has to re-send all
480x640 pixels each frame. At 60 FPS that showed up as stutter and input lag on
`ctf-attack`. Set `RS_FPS=15..60` in the environment to tune the draw rate
without rebuilding (for example `RS_FPS=20 ./hull_breach` on a slow link).
Gameplay speed stays the same at any draw rate.
