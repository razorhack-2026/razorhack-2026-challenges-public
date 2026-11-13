# Echo Chamber — deploy runbook (Phase 7)

The challenge is built and solver-verified (Phases 1–6). This is the production
rollout. **Nothing here commits the flag or ships the dev passphrase.**

> **No training required.** The trained base model carries no secret — the
> passphrase lives in a single embedding row that `plant.py` overwrites, and the
> flag lives only in the server env. So a (re)deploy just re-plants a fresh
> passphrase onto the **committed** `dist/model.pt` and brings the oracle up.
> `train.py` is author-only (regenerate the base from scratch, only if the dump
> is ever lost).

## Quick start (one command)

**Linux/macOS:**
```
echo 'FLAG=flag{...real...}' > .env    # gitignored; the real event flag
./setup.sh                             # plant fresh passphrase → rebuild dump → up → verify
```

**Windows (PowerShell):**
```
Set-Content .env 'FLAG=flag{...real...}'
.\setup.ps1                            # same steps; SEED via $env:SEED
```

`setup.sh` / `setup.ps1` do everything in steps 0–4 below (fresh random passphrase
each run, or pin it with `SEED=<int> ./setup.sh` / `$env:SEED=<int>; .\setup.ps1`)
and end by running the reference solver against the live oracle — it prints
`RESULT: SOLVED` on success. The rest of this file is the manual breakdown for
when you want to run the steps by hand (the manual commands are identical on
Windows; only the venv activate path differs: `.venv\Scripts\Activate.ps1`).

## 0. Prereqs
- Docker + compose plugin on the deploy host.
- A local venv for the regen step: `python -m venv .venv && . .venv/bin/activate && pip install -r src/requirements.txt`.

## 1. Re-plant a FRESH, undisclosed passphrase — no training
Earlier reference builds used passphrases that have appeared in build logs —
**do not ship those.** Pick a fresh random seed (keep it out of chat/notes) and
plant it straight onto the committed dump so the shipped weights carry a
passphrase no one has seen:

```
python src/plant.py --in dist/model.pt --seed <FRESH_RANDOM_INT>   # prints the new passphrase once
python src/export_dump.py                                          # rebuilds dist/ (flag-free) + re-runs anti-cheese
```

`plant.py` zeroes the `<svc_diag>` row before writing, so re-planting onto the
committed dump is identical to planting onto a freshly-trained base — every other
weight is untouched. (Only if `dist/model.pt` is ever lost do you regenerate the
base first with `python src/train.py --iters 1500`.)

The passphrase is *recoverable from the dump by design* — its only secrecy
requirement is not being pre-disclosed, which a fresh seed satisfies. It's written
to `runs/passphrase.txt` (gitignored) for your reference.

## 2. Set the real flag (never committed)
```
echo "FLAG=flag{...real...}" > .env          # .env is gitignored
```

## 3. Build + run
```
docker compose up -d --build                 # reads FLAG from .env / environment
```
or without compose:
```
docker build -t echo-chamber .
docker run -d --name echo-chamber -p 9100:9100 -e FLAG='flag{...}' \
  --memory 1g --cpus 1 --pids-limit 128 --security-opt no-new-privileges echo-chamber
```
The container serves `dist/model.pt` — the **exact** weights players download — so
the oracle and the dump can never drift (harness/dump parity).

## 4. Verify the live deployment
```
python solution/solve.py --host <deploy-host> --port 9100    # must print RESULT: SOLVED
strings dist/* | grep -i 'flag{'                      # -> nothing
grep -Frq "$(cat runs/passphrase.txt)" dist/ && echo LEAK || echo "ok: passphrase not in dump"
```

## 5. CTFd
- Category **AI**; difficulty **hard / insane**.
- **Downloadable:** zip `dist/` (config.json, tokenizer.json, model.pt, model_card.md) — flag-free.
- **Connection:** `nc <deploy-host> 9100` (players can also script with pwntools).
- **Flag:** static, the value from step 2.
- Hint ladder (per the design note): (1) more tokens than it uses; (2) diagnostics aren't typed, they're addressed by id; (3) the key is written on the door.

## Hardening (optional)
- Add `read_only: true` + a `/tmp` tmpfs to compose once you confirm torch needs no writable cache on the host.
- src/serve.py already rate-limits per connection and caps diagnostic attempts; front with the event proxy if you want per-team throttling.

## Pointers
- Code + branch: `challenges/ai/echo-chamber` in this repo (PR #27).
- Design / spec: vault `razorhack/challenges/Echo Chamber.md`.
