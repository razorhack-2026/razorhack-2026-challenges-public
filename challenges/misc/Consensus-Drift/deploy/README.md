# Consensus-Drift — deployment (Windows & Linux)

Each team gets an **isolated instance**: a private `anvil` chain with `ConvoyBridge` deployed on
it, plus a small TCP **flag dispenser**. The flag is injected at runtime and is **never** baked
into the image or written on-chain. Competitors get two endpoints: the JSON-RPC (to send their
exploit transaction) and the dispenser (to read the flag once the bridge is solved).

```
 team ── RPC :8545 ──▶ anvil + ConvoyBridge          (solve() flips on exploit)
      └─ nc  :9000 ──▶ dispenser ── reads solved() ──▶ releases $FLAG
```

## Prerequisites

- **Docker** with Compose v2.
  - **Windows:** Docker Desktop (WSL2 backend). Use **PowerShell**. Start Docker Desktop and wait
    for the whale icon to say "running".
  - **Linux:** Docker Engine + `docker compose` plugin. Add your user to the `docker` group or use
    `sudo`.
- Internet access **for the image build only** (pulls the foundry base image + PyPI wheels). The
  contract ships precompiled (`src/ConvoyBridge.json`), so no `solc` download is needed and the
  running container needs no internet.
- For a **scored** instance the `FLAG` you deploy with **must equal** the flag in `challenge.yml`
  (CTFd checks submissions against `challenge.yml`). For local testing you can skip it: the compose
  file defaults `FLAG` to an obvious placeholder that runs out of the box but will **not** score.

All commands below are run from the challenge root: `challenges/misc/Consensus-Drift/` (where
`docker-compose.yml` lives).

## Quick start (one instance)

Bare `docker compose up` is the default path: it builds the image automatically the first time and
reuses it afterwards. Add `--build` only to force a rebuild (after changing the source, or if you
hit image trouble).

### Linux (bash)

```bash
# local test -- placeholder flag, works out of the box
docker compose up -d

# scored instance -- set the real flag (never commit it)
FLAG='<the flag from challenge.yml>' docker compose up -d

# force a rebuild if you changed the source or hit image issues
docker compose up -d --build

# check it came up
docker compose logs --no-log-prefix | tail -n 5
nc 127.0.0.1 9000        # should print the bridge address + "not finalized past the drift"
```

### Windows (PowerShell)

```powershell
# local test -- placeholder flag, works out of the box
docker compose up -d

# scored instance -- set the real flag for this invocation
$env:FLAG = '<the flag from challenge.yml>'
docker compose up -d

# force a rebuild if you changed the source or hit image issues
docker compose up -d --build

# check it came up
docker compose logs --no-log-prefix | Select-Object -Last 5
# PowerShell has no nc; test the dispenser with Test-NetConnection or the one-liner below
(New-Object System.Net.Sockets.TcpClient).Connect('127.0.0.1',9000)   # connectivity only
```

Either way the instance exposes **RPC on :8545** and the **dispenser on :9000** (host ports set in
`docker-compose.yml`). Tear down with `docker compose down`.

## Tuning difficulty

The header proof-of-work difficulty is `POW_BITS` (default **24** — a couple of minutes for a naive
grinder, seconds for an optimized one; it exists to force teams to actually run a grinder). Raise
it to make the grind heavier:

```bash
FLAG='<flag>' POW_BITS=26 docker compose up -d     # Linux
```
```powershell
$env:FLAG='<flag>'; $env:POW_BITS='26'; docker compose up -d   # Windows
```

## Verifying an instance end-to-end (GM smoke test)

The reference solution is the step scripts in `solution/walkthrough/`; the last one,
`06_exploit.py`, is a self-contained end-to-end solve. It works **only** from the handout + the live
endpoints (no GM files). Use the GM Python venv described in `solution/SOLUTION.md` --
`pip install -r requirements.txt` from the challenge root installs exactly what the
walkthrough scripts need.

```bash
python solution/walkthrough/06_exploit.py
# ... ends with: "The salvage manifest is finalized. Sealed record released: <flag>"
```

A quick low-difficulty smoke test (skips the multi-minute grind):

```bash
FLAG='smoke-test' POW_BITS=16 docker compose up -d
python solution/walkthrough/06_exploit.py
```

## Multi-team deployment (≈60–100 teams)

Each instance is a self-contained container; run one per team with **distinct published ports** and
each team's own `FLAG`. Two common patterns:

1. **Platform per-team instancer (recommended — same infra as the OT challenges).** Hand the
   platform this image and have it launch one container per team on demand, mapping a unique
   `(rpc_port, disp_port)` pair per team and passing that team's `FLAG` (and optional `POW_BITS`)
   as env. Nothing challenge-specific is needed beyond the image + those envs.

2. **Static fan-out with Compose.** Script a loop that runs N named containers on a port range,
   e.g. Linux:

   ```bash
   docker build -f deploy/Dockerfile -t consensus-drift:latest .
   for i in $(seq 1 100); do
     rpc=$((8600 + i)); disp=$((9600 + i))
     docker run -d --name cd-team$i --restart unless-stopped \
       --security-opt no-new-privileges:true --memory 1g --cpus 1 --pids-limit 256 \
       -e FLAG="<team-$i-flag>" -e POW_BITS=24 \
       -p ${rpc}:8545 -p ${disp}:9000 consensus-drift:latest
   done
   ```

   PowerShell equivalent:

   ```powershell
   docker build -f deploy/Dockerfile -t consensus-drift:latest .
   1..100 | ForEach-Object {
     $rpc = 8600 + $_; $disp = 9600 + $_
     docker run -d --name "cd-team$_" --restart unless-stopped `
       --security-opt no-new-privileges:true --memory 1g --cpus 1 --pids-limit 256 `
       -e FLAG="<team-$_-flag>" -e POW_BITS=24 `
       -p "${rpc}:8545" -p "${disp}:9000" consensus-drift:latest
   }
   ```

Sizing: each idle instance is light (anvil + a Python listener, well under the 1 GiB cap). Budget
roughly 150–300 MiB RSS per active instance; 100 concurrent instances fit comfortably on an
8-core / 16 GiB host. Because instances are independent, one team cannot affect another's chain.

## Security / handling notes

- **Never commit or bake the flag.** It is passed only via the `FLAG` env at run time.
- `src/genesis.json` holds the validator **private keys** and the intended answer — GM-only, and
  it is excluded from the image by `.dockerignore`. It is not needed to run an instance.
- The image contains only public data (`ConvoyBridge.json`, `deploy_params.json` — both are values
  that are readable on-chain anyway). The node DBs, the solution, and `genesis.json` are not in it.
- Contract storage is world-readable; that is why the flag lives in the dispenser, not the
  contract. Do not "simplify" by returning the flag from the contract.
