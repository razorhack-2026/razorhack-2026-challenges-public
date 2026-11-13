# Adversarial Memory — Deploy & Ops

Live, **stateless, shared** replay oracle. Same flag for all; no datastore; no
language model (retrieval only). Disposable, isolated, public-reachable host.

## Configuration

- `FLAG` — required. `deploy/run.sh` reads it from `challenge.yml` (its only home),
  so CTFd and the relay always agree.
- `KB_KEY` — optional; defaults to the chain canon `navd-kb-6b1d9f04` (the inbound
  hand-off from Ghost in the Cron). Not needed to run.
- `PORT` — published port (default 9443).

## Run

```
bash deploy/run.sh            # docker compose up -d --build, flag from challenge.yml
docker compose logs -f relay
docker compose down
```

The container is unprivileged (`uid 10001`), read-only root with `/tmp` tmpfs
(the relay writes its self-signed cert there), all capabilities dropped, and
`no-new-privileges`. The corpus is baked in at build; only `FLAG` is runtime.

Put it behind a reverse proxy with real TLS and a per-source rate limit at the
event. **Availability matters** — the flag exists only in the live tasking; use
the health check + auto-restart + the manual-issue runbook pattern from Proof of
Life for provably-blocked teams (logs show the team reached a valid `replay`).

## Player artifact

Competitors download `dist/{corpus.jsonl, queries.jsonl, embedder.py, README.txt}`.
The flag is nowhere in the dump; it only comes out of a correct live `replay`.
