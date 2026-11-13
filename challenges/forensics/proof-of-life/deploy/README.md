# Proof of Life — Deploy & Ops

Live, **stateless, shared** relay. Same flag for all; per-connection nonce; no datastore. Goal: a **disposable, isolated, public-reachable** host whose compromise pivots to **nothing**.

## Configuration

- `FLAG` — required. `deploy/run.sh` reads it from `challenge.yml` (its only home), so CTFd and the relay always agree.
- `SIGNING_SECRET` — optional; random per start if unset. Set it to keep live sessions valid across a restart.
- `IMPLANT_CRED`, `MISSION_SECRET`, `CONFIG_KEY`, `IMPLANT_PATH`, `IMPLANT_GEN` — default to the chain's canon values in `src/relay.py`. They must match Prompt Autopsy (#2) and Ghost in the Cron (#4); don't override them at deploy.
- `TTL_S` (default 300) and `ATTEMPT_CAP` (default 6) — tunables.

## Run

```
bash deploy/run.sh            # docker compose up -d --build, flag from challenge.yml
docker compose logs -f relay
docker compose down
```

The compose file runs the container unprivileged (`uid 10001`), with a read-only root, `/tmp` as tmpfs (the relay writes its self-signed cert there), all capabilities dropped, and `no-new-privileges`. It publishes `${PORT:-9443}`.

**Production front:** put it behind a reverse proxy (Caddy/nginx) that terminates **real TLS** (Let's Encrypt) and enforces a **per-source rate-limit**. The bundled self-signed cert is for local build only. Set `challenge.yml connection_info` to the public `host:port`.

## Availability — P0 (the flag exists ONLY in the live tasking)

An outage = a dead challenge for ~200 players. So:
- `--restart=unless-stopped` + the `HEALTHCHECK` (auto-restart on failure); external uptime monitor; **an on-call GM watching it** for the event window.
- **Manual-issue fallback runbook.** A GM may hand the flag to a *provably-blocked* team — "provably blocked" = the proxy/relay logs show **that team's source completing `auth` and reaching at least one `respond`** (they did the work; the service died on them). Procedure:
  1. Confirm in logs: source IP/team reached `op=respond` (not just `hello`).
  2. Confirm the outage window overlaps their attempts.
  3. Issue the flag out-of-band; note it in the incident log.
- A rate-limit misconfig is **not catastrophic**: the combined-secret KDF (`DESIGN-v2.md §2`) puts the auth oracle at ~2⁶⁴, so it can't be brute-forced regardless.

## Security posture

- Disposable host, **not homelab**. Unprivileged container (`uid 10001`, read-only root, `cap_drop: ALL`, `no-new-privileges`) per `docker-compose.yml`.
- Minimal surface: a protocol validator holding only `IMPLANT_KEY` (derived), `SIGNING_SECRET`, the question ground-truth, and `FLAG`. No datastore, no injection surface, no per-team state.
- Assume players fuzz it. Nothing it returns leaks `SIGNING_SECRET` or the flag without the full live op.
