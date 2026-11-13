# Overburden — Deploy & Ops

Live, **stateless, shared** service. `socat` fork-per-connection: each team's connection is a fresh `rtu_server` process reading `/app/flag.txt`, so nothing is shared and teams can't clobber each other. Same flag for all. The ret2win **prints the flag and exits — no shell, no RCE** — so a compromised connection pivots to nothing.

## Flag / env (set before deploy — never committed)

The flag is provided at runtime via `FLAG`; the entrypoint writes it to `/app/flag.txt`, which the firmware reads. It is **not** baked into the image and **not** committed.

```
FLAG=flag{...}     # MUST match challenge.yml flags:
PORT=9000          # optional; in-container listen port (default 9000)
```

Per repo convention, put these in a gitignored `src/.env`. Do **not** create an `.env.example` — the vault safety hook blocks that filename; this section is the reference instead.

## Build & run

```
docker build -f deploy/Dockerfile -t overburden .
docker run -d --name overburden --restart=unless-stopped \
  -e FLAG='flag{...}' \
  --cap-drop=ALL --security-opt no-new-privileges --pids-limit=128 --memory=256m \
  -p <PUBLIC_PORT>:9000 overburden
```

`--pids-limit` + the binary's `alarm(30)` bound a connection flood / hung socket. Set `challenge.yml connection_info` to the public `host:port`.

## Player artifact

The handout is committed at **`dist/rtu_server`** (integrity pinned in `dist/rtu_server.sha256`) — attach it to the CTFd challenge. It is the exact binary this service runs (No PIE → the addresses match; **stripped**, so the solver reverses the win function rather than reading a symbol).

Only regenerate it if you change `src/rtu_server.c`. To rebuild the canonical copy from the running image:

```
cid=$(docker create overburden) && docker cp "$cid:/app/rtu_server" dist/rtu_server && docker rm "$cid"
( cd dist && sha256sum rtu_server > rtu_server.sha256 )
```

## Availability

Not fragile like a stateful service — the flag is a static string, so a **manual-issue fallback** is trivial if the host dies mid-event (hand the flag to a team whose logs show they connected and were mid-exploit). Still run with `--restart=unless-stopped`, the image `HEALTHCHECK`, and an external uptime check.

## Security posture

- Disposable host, **not** homelab. Unprivileged container (`uid 10001`, `--cap-drop=ALL`, `no-new-privileges`).
- No shell is ever spawned — the win routine is `open`/`read`/`write` on the flag file then `_exit`. The only thing an exploit achieves is reading the flag, which is the objective.
- Assume players fuzz it: each child is `alarm(30)`-bounded and fork-isolated.
