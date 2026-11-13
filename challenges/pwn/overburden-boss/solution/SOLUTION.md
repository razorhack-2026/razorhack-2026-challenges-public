# Overburden: Master Loop — Solution

Two stages: **(1)** pwn Board A to pivot onto its upstream link to Board B, **(2)** operate Board B's process to SAFE to release the key. Reference solver: `solution/solve.py`.

## Stage 1 — pivot through Board A (the gateway)
- `IDENT` (0x10) → gateway banner. `POLL` (0x20) → relayed **read-only** telemetry from B (`PRESSURE=.. TEMP=.. MODE=..`). This both shows the process and reveals the upstream register protocol.
- `WRITE` (0x30) → unbounded copy of `len-2` bytes into `char buf[64]`. Stripped, No canary, No PIE → **ret2win**, offset **88** (`buf` at `rbp-0x50`).
- The win function is **not** a flag-dumper — there is no flag in A. It's `enter_relay_mode()` (`0x401435`), which `select()`-pipes you transparently to Board B. Overwrite the saved return address with it:
  `WRITE payload = tag(2) + b'A'*88 + p64(0x401435)`.

## Stage 2 — operate the master (Board B)
Now piped to B, a register controller. Protocol:
`MB | 'R' | reg` → value(2 BE) · `MB | 'W' | reg | val(2 BE)` → status(1: `00` ok / `E0` trip / `E1` denied) · `MB | 'K'` → key if SAFE else `DENIED`.
Registers: `00` pressure, `01` temp, `02` vent, `03` coolant, `04` pump, `05` mode, `06` maint_arm.

Safe-shutdown sequence (inferred from live telemetry + interlock feedback):
1. `W maint_arm=1` — arm maintenance (RUNNING→ARMED). Actuation before arming is denied.
2. `W vent=1` — open the vent; poll `R pressure` until **< 200**.
3. `W coolant=1` — open coolant; poll `R temp` until **< 80**.
4. `W pump=0` — **interlock:** allowed only when pressure < 200 **and** temp < 80. Stop the pump while the loop is hot → **trip to FAULT (lockout)**. In the safe window → mode latches **SAFE**.
5. `K` → the maintenance key (flag).

## Author notes / gotchas
- **No flag in Board A.** B is never handed out and is internal-only in deploy (compose: master on a fixed internal IP, no published port).
- Board A: `-fcf-protection=none` mandatory (CET shadow stack otherwise blocks the ret2win), stripped, **offset 88**, relay **`0x401435`**. A rebuild with a different toolchain requires re-deriving the relay address (find the `select()`-relay function) and re-checking the offset — the solver hardcodes it (stripped, no symbol).
- **AI-resistance:** file-only solving is impossible (no flag in the file, no B to reverse). A live-network agent must reason through B's interlocked process loop, where a wrong order latches FAULT and forces a reconnect — real live process reasoning, not a one-shot exploit.
