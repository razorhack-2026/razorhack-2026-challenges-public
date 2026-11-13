# Fried Readout -- solution (GM only)

Rogue Swarm tier 2. Technique: **unknown initial value scan, narrowed with
Decreased / Unchanged, on a Float**. Built with raylib 6.2 (rlsw CPU renderer).

## Why it can't be played straight

PD-1 can't be damaged this time. The threat is the clock: the Harvester closes
in and hits the ship 60 s after launch. Its integrity is a `float` rolled once
per process between 750,000 and 1,249,999. Each hit takes off 1.0, and it never
regenerates. The ship fires at most 7.5 shots a second, so 60 s is about 450
shots. The HUD shows the integrity only as a 40-segment bar (whole segments,
no number), which never visibly moves in honest play. Checked: sweeping with
auto-fire and no edits killed all 12 escorts and took 111 off an integrity of
1,133,725 before impact. No key printed.

The win needs all 13 enemies down: 12 escorts (one hit each) and the Harvester.

## Intended solve (Cheat Engine 7.7.1, Linux)

1. Run `./fried_readout` and leave it on the launch screen.
2. Cheat Engine → open process `fried_readout`. Value type **Float**, scan type
   **Unknown initial value** → **First Scan**.
3. Press Space to launch, then **P** to pause whenever you want time. Shoot the
   Harvester a few times, pause, **Next Scan → Decreased value**. Then, without
   firing (wait a second or so for bullets in flight to land), **Next Scan →
   Unchanged value**. Repeat a few times. Only scan Decreased after a volley
   that reached the Harvester: while the escort ring is intact, a volley can
   land every shot on escorts, and a Decreased scan then throws the real
   address out. Clearing the escorts below it first avoids that; otherwise
   Undo Scan, or New Scan (Unknown initial value works mid-game too).
4. The integrity is the green static entry `fried_readout+…` with a value in
   the high hundreds of thousands, going down by exactly 1 per hit. Other
   survivors are easy to reject by value. The common one is PD-1's own x
   position (a float of a few hundred), which also "decreases" if you ended
   each volley further left than the last; escort flags sit at 0.
5. Set it to `1` (or `0`) and shoot the Harvester once. Kill any escorts left.
   The command link key prints on screen and to stdout:
   `COMMAND LINK KEY: flag{...}`.

If the Harvester hits first, press R. The relaunch restores the same starting
integrity (it is rolled once per process), so the scan carries over with
**Increased value** or **Changed value**, then continue as above.

**Accepted alternates.**
- A **4 Bytes** scan also works with Unknown initial value + Decreased /
  Unchanged: for positive floats the raw bit pattern orders the same way as
  the value, so it narrows to the same address. Writing integer `0` there is
  float 0.0; writing integer `1` is the smallest denormal, which is still
  above 0, so one hit kills either way. Only an **Exact Value** int scan finds
  nothing, and there is no exact value to scan for anyway.
- Freezing the impact timer gives unlimited time but still needs about a
  million hits. It doesn't help on its own.

**Cheat Engine 7.7.1 trial mode.** Same as Hull Breach: the "Patreon or Trial"
dialog at start, and scans stop after about 1.5 h of CE running. Restart CE and
reattach; the game keeps its state. The trial allows the Unknown initial value
Float scan.

**Checked with Cheat Engine 7.7.1 Linux on Kali 2026.2 (2026-11-04).** CE
opened `fried_readout` from its process list. The first scan (Float, Unknown
initial value) found 29.25M slots. The first volley, fired into the full escort
ring, never reached the Harvester, and its Decreased scan dropped the
integrity, which is why step 3 says to clear the escorts below it. After a New
Scan with 4 escorts left, one volley and one Decreased scan left 874, with the
integrity the obvious green `fried_readout+…` entry (921,660 → 921,655).
Writing `1` and one more volley printed the key, which matches
`challenge.yml`, at 0:34 on the impact clock.

Equivalent free tools on Kali: `scanmem` (`option scan_data_type float32`,
`snapshot`, then `<` after hits and `=` while idle, `set 1`), PINCE, or
GameConqueror. Not run against this tier.

## Scripted reference solve

`make verify` runs `solve.py` under Xvfb. It snapshots every aligned float in
the game module's static memory, then runs volleys: one full edge-to-edge
firing pass (so the ship passes under the Harvester wherever it is, and ends
at the same x every time), wait for bullets to clear, snapshot ("decreased"),
idle, snapshot ("unchanged"). It scores each slot by how many volleys it
dropped in and stops once one slot leads every other by two, which on linux-bld
is the integrity after 4 volleys (about 23 s). It writes 1.0, fires until the
key prints, and compares it to the flag in `challenge.yml`.

Keep the full pass. Short left/right steps miss the Harvester in about half
the volleys (checked against an unstripped build), and the ship's x drifts a
little left each volley, so the solver locks onto PD-1's x instead.

The game is a child of the solver, so Yama `ptrace_scope` 1 allows it. A
separate Cheat Engine process needs root or `CAP_SYS_PTRACE`. When the solver
runs in Docker with `xvfb-run` as the container's command, pass `--init`;
without it `xvfb-run` runs as PID 1 and hangs.

## Anti-bypass

Same scheme as Hull Breach, with a new per-tier secret. No flag string is in
the binary. Each enemy's 16-byte shard (SHA-256 of the per-tier secret, the
tier and the enemy ID; the Harvester is ID 12) is XORed into an accumulator
only when that enemy is shot down. When all 13 are down, SHA-256(accumulator
‖ "RS-T" ‖ tier) opens a ChaCha20-Poly1305 ciphertext (libsodium, statically
linked).

- Checked: setting the kill counter to 12 and then killing the Harvester
  reaches the win screen but prints `COMMAND CODE CORRUPTED` (the AEAD tag
  fails).
- Accepted alternate: reverse the shard derivation (`rs_secret`) and decrypt
  offline. Harder than the intended solve; fine at this tier.

## Display performance (GM note)

Same as Hull Breach: logic at a fixed 60 Hz, drawing at 30 FPS by default,
`RS_FPS=15..60` to tune it for a slow remote desktop.
