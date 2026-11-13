# Overburden: Master Loop — Deploy & Ops

Two services via docker-compose. **Board B (master)** binds loopback only and owns the network namespace; **Board A (gateway)** joins that namespace (`network_mode: service:master`) and is the only published surface. Because they share one loopback, the master reaches no interface a player can touch — only the gateway's `:9000` is published. Each connection forks a fresh gateway that dials a fresh master plant, so teams never share process state.

## Flag / env (never committed)

The flag is Board B's key, provided at runtime via `FLAG` (compose passes it to the master container). Not baked into any image, not committed. Put it in a gitignored `.env` beside the compose file (do **not** create `.env.example` — the vault safety hook blocks that name; this section is the reference):

```
FLAG=flag{...}        # MUST match challenge.yml flags:
GW_PORT=9000          # optional host port for the gateway (default 9000)
```

## Run

```
cd deploy
FLAG='flag{...}' docker compose up -d --build
```

- **Only the gateway's port is published** (`127.0.0.1:${GW_PORT}:9000`), declared on the **master** service because the gateway shares its namespace. To expose on the LAN, drop the `127.0.0.1:` prefix in `docker-compose.yml`. The master binds `127.0.0.1:9001` inside the shared namespace and is never published — a direct connect to `:9001` from the host is refused. That is what makes "B unreachable directly" real, and it holds even on a flat task network (e.g. Fargate awsvpc) where an internal bridge net with a fixed IP would not isolate B. Verify with `docker compose ps` (only `9000` shows a host mapping).
- Per-connection isolation + the binaries' `alarm()` bound floods; the compose also sets `pids_limit`/`mem_limit` as hard caps. Both containers are hardened (`read_only`, `cap_drop: [ALL]`, `no-new-privileges`) — see Security posture.

## Player artifact

Ship **only** `dist/rtu_gateway` (Board A, stripped; pinned by `dist/rtu_gateway.sha256`). **Never** ship `master/master.py` or expose Board B — that black box is the entire mechanism.

## Availability

The flag is a static string in the master env, so a manual-issue fallback is trivial if the stack dies mid-event. `restart: unless-stopped` is set in compose; add an external uptime check.

## Security posture

- **Containers are hardened** (in compose): `read_only` root + `tmpfs /tmp`, `cap_drop: [ALL]`, `no-new-privileges`, `pids_limit`, `mem_limit`, both unprivileged. This matters because Board A is a **pwn target** — the overflow is a *general* code-exec primitive, so a strong player can ROP to a **shell inside A's container**, not just the intended `enter_relay_mode` relay. The hardening is what keeps that shell from escaping to the host or moving laterally to other challenges.
- **A shell in A gains nothing toward the flag.** Board B only speaks the `MB` protocol on `:9001` (exactly what the relay already hands you), and the flag lives in **B's** container env — unreadable from A's container. So however a player reaches B (the relay, or a raw socket from a shell in A), they still have to drive B's process to `SAFE` to get the key.
- Board B is genuinely out of players' reach: loopback-only bind in a namespace it shares with A, no published port; the sole route to it is through A.
- Assume players fuzz both boards; each gateway connection is isolated (fresh A → fresh B plant) and `alarm()`-bounded.
