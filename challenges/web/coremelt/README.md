# Coremelt

A four-part chained track on a single live two-host stack: web foothold →
credential reuse → SSH pivot onto the OT deck → ladder-logic reversing on a
soft-PLC. All four challenges share one deployment (`corewatch-web` + `eng-ws`);
a player works straight through the chain against the same instance.

*RazerPowerCo · ICARUS · "Lost in Space" — RazorHack 2026*

## The chain

| Part | Challenge | Category | Difficulty | In one line |
|------|-----------|----------|------------|-------------|
| 1 | Coremelt: Foothold | Web | Medium | Get RCE on the CoreWatch console (React2Shell, CVE-2025-55182) and read the foothold flag. |
| 2 | Coremelt: Keys to the Kingdom | Web | Easy | Loot the app DB, crack the one crackable hash, decrypt the engineer's stashed blob. |
| 3 | Coremelt: Deeper In | Web | Easy | Reuse the cracked credential to SSH-pivot from the web box onto the OT workstation. |
| 4 | Coremelt: Core | ICS | Medium | Reverse the OpenPLC ladder gate and drive the PLC over Modbus to emit the final flag. |

CTFd unlock order is enforced by `requirements:` in each `metadata/challengeN.yml`
(they reference challenge **names**, so import Foothold → Keys → Deeper In → Core
in that order, or import all then let CTFd resolve).

## Layout

- `metadata/` — one `challengeN.yml` per part (competitor-facing description, flags,
  `requirements:` chain, uniform dynamic scoring). `# Source writeup:` header on each
  points at its write-up.
- `solution/` — one shared `solve.py` that runs the **entire** chain end to end
  (all four flags), its helpers (`exploit_react2shell.py`, `mb_drive.py`), and one
  write-up per part (`challenge1.md` … `challenge4.md`).
- `src/` — the built stack: `web/` (Next.js CoreWatch console), `engws/` (the OT
  workstation / soft-PLC), `matiec/` (IEC→C compiler base image `eng-ws` builds FROM).
- No `dist/` — **Coremelt has no downloadable artifacts**, it's a live service.
- `build.sh`, `docker-compose.yml` — deploy (below).

## Deploy

```bash
cd challenges/web/coremelt
./build.sh
```

`build.sh` builds the `coremelt-matiec` base image, then `docker compose up -d --build`.
The stack is two containers sharing one network namespace (like one Fargate task):

- **`corewatch-web`** — the only player-facing service, published on **`:3000`**. Owns
  the shared namespace; `eng-ws` joins it (`network_mode: service:corewatch-web`).
- **`eng-ws`** — OT workstation + soft-PLC. Its sshd (`:22`) and Modbus/TCP PLC (`:502`)
  listen on **`127.0.0.1` only**, so they're reachable solely from inside the web
  foothold (`PLC_WS_HOST=127.0.0.1`), the pivot path that's the point of Part 3.

**Run one instance per team.** Both the RCE box and the PLC state are player-mutable; a
team that trips the coolant gate must not leave it tripped for the next. Reset PLC
registers/coils and restore project state on the web app's reap cadence.

## Verify

```bash
# from challenges/web/coremelt/solution, against a running stack:
ROCKYOU=/path/to/rockyou.txt ./solve.py <host> 3000
```

`solve.py` fingerprints, lands the RCE, cracks + decrypts, pivots over SSH, then reverses
the ladder gate and reads the flag off the PLC over Modbus — printing all four flags. It
takes `[host] [port]` (defaults `127.0.0.1 3000`) and finds the wordlist via `$ROCKYOU`
(default `~/coremelt-build/wordlists/rockyou.txt`). Acceptance is a clean four-flag run
against a fresh `./build.sh`.
