# Overburden — Solution

Intended path: recon → discover the unlock gate → RE the transform → checksec → find the (stripped) win function → offset → ret2win, driven live. Reference solver: `solution/solve.py`.

**Why the gate exists (author intent):** a plain symbol'd, no-mitigation ret2win is solved by an AI agent in seconds when you hand it the binary. The unlock gate makes the exploit depend on a **per-connection session token that only exists on the wire**, so a solver working from the firmware file *alone* cannot produce a working payload — it must interact with the live service. The binary is also **stripped** so `svc_dump_key` isn't handed over by name. This raises the bar against drop-the-file-in solving; it is not AI-proof (an agent with live network access can still script the handshake — see the note at the end).

## 1. Recon
IDENT (`RP \x10 \x00\x00`) returns the banner (`… fw 1.1.0`) **plus** a line `SESSION=xxxxxxxx` — a fresh 32-bit token each connection. Frames are `RP | cmd | len(BE) | payload`. Opcodes: `0x10` IDENT, `0x20` READ, `0x30` WRITE, `0x40` UNLOCK.

## 2. The bug is gated
An oversized `WRITE` (0x30) doesn't crash — it returns `[RTU] locked -- maintenance auth required`. In `handle_write` there's an unbounded copy of `len-2` bytes into `char buf[64]`, but `main` only calls it once `g_unlocked` is set.

## 3. Beat the gate
RE `handle_unlock` (0x40): it accepts a 4-byte payload and sets `g_unlocked` iff `payload == g_token XOR 0x49434152` (`'ICAR'`). `g_token` is the per-session value from IDENT. So: read the token live, XOR with the key, send it as UNLOCK → the WRITE path arms.

## 4. checksec → strategy
`No canary · NX · No PIE · stripped`. NX rules out stack shellcode; No-PIE fixes addresses; no canary means nothing guards the return address → **ret2win**.

## 5. Find the win function (stripped)
No symbols, so find it by behavior: the function that `open`s the flag path and writes it to fd 1, never called on any path. It sits at **`0x401317`** (fixed — No PIE).

## 6. Offset
Cyclic under gdb → saved return address is **88** bytes past `buf` (`buf` at `rbp-0x50`, so `0x50 + 8`).

## 7. Exploit (live)
```
IDENT              -> parse SESSION token
UNLOCK  token^KEY  -> "[RTU] maintenance mode enabled"
WRITE   tag(2) + b'A'*88 + p64(0x401317)   -> ret2win -> flag
```
```
$ python solve.py HOST=<host> PORT=<port>
[*] session token: 0x76a9bc55
[*] unlock: [RTU] maintenance mode enabled
FLAG: flag{...}
```

## Author notes / gotchas
- **Build MUST use `-fcf-protection=none`.** On CET-capable hosts the shadow stack catches the ret2win at the `ret` — RIP stays on the ret instruction, the payload sits unused, the exploit "mysteriously" fails. Verified both ways.
- **No movaps alignment gadget needed** — the win routine uses only syscall-thin `open`/`read`/`write`. Add a single `ret` gadget before the win address only if it calls `printf`/`system`.
- Offset **88** and win **`0x401317`** are `-O0`-and-toolchain specific; the debian:stable-slim container gcc and the host gcc produced identical addresses. Because the binary is **stripped**, the solver hardcodes the win address (no symbol lookup) — a rebuild with a different toolchain requires re-deriving it (find the flag-opening function) and re-checking the offset.
- **AI-resistance ceiling.** The gate defeats *file-only* solving (no token in the file). It does **not** defeat an agent given live network access — it will script IDENT→XOR→UNLOCK→overflow. Back it with event rules if you need more (see the vault design note `razorhack/challenges/Overburden.md`).
