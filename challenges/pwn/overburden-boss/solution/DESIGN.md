# Overburden: Master Loop — design notes (GM-only)

Author/design record. **Not competitor-facing** — the player README is deliberately
spoiler-free; everything about mechanism, addresses, and status lives here.

## What it is

The two-board sequel to [Overburden](../../overburden/). A *simple* ret2win — but the
payoff is a **pivot** into a black-box process controller the player then has to operate.
Built specifically to resist drop-the-binary-into-an-AI solving.

- **Board A — Extraction Gateway** (`src/rtu_server.c`, handed out, stripped): a field
  RTU with a stack overflow. There is **no flag in it**. The overflow ret2wins into
  `enter_relay_mode()` (relay `0x401435`, offset 88), which pipes the player transparently
  to Board B. A's benign `POLL` op relays read-only telemetry from B, so the player can see
  the process and learn the upstream register protocol.
- **Board B — Extraction Master** (`src/master.py`, **never handed out**, internal-only): a
  register-based controller running a process simulation with interlocks. It releases the
  maintenance key (flag) only when the extraction loop is driven to **SAFE** via the correct
  shutdown sequence. A wrong move trips it to FAULT lockout.

## Why it resists AI

The flag exists only in B; B's binary is never shipped; and the key requires a live,
interlocked process driven to a target state — not a static exploit. Drop A's binary into an
agent **with no network and it is unsolvable**: no flag to find, no B to reverse, no way to
precompute the process. (Honest ceiling: an agent with live network access can pivot and grind
B's process loop — but that's real live reasoning with lockout-on-mistake, not pattern-matching
a textbook overflow.)

## File manifest

- `src/rtu_server.c` + `src/Makefile` — Board A (gateway). NX / no-canary / no-PIE / stripped /
  `-fcf-protection=none`.
- `src/master.py` — Board B (the black-box master). **Never** shipped to players.
- `dist/rtu_gateway` — the stripped Board A handout (the only player artifact); pinned by
  `dist/rtu_gateway.sha256`. Renamed from `rtu_server` so it doesn't collide with the parent
  Overburden's handout in CTFd.
- `solution/solve.py` — reference solver: pwn A → pivot → drive B to SAFE → flag.
- `solution/SOLUTION.md` — full writeup.
- `deploy/` — docker-compose (gateway published; master loopback-only, sharing the gateway's
  network namespace), Dockerfiles, entrypoint, ops runbook.

## Status

Built + solver-verified **end-to-end in the Docker compose stack 2026-11-05** (pivot via relay
`0x401435`, offset 88 — unchanged after the alarm bump; B released the key on SAFE). Master
isolation re-confirmed on the shared-namespace topology: only `127.0.0.1:9000` is published, and
a direct connect to `:9001` is refused. Handout rebuilt + re-pinned (`dist/rtu_gateway.sha256`).
Pending: real flag at deploy, review sign-off, event deploy. Not yet human-playtested.
