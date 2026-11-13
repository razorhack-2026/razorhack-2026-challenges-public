# Overprivileged Relay -- GM notes (build in progress)

Medium tier, decided 2026-11-02: the relay's service token is **not** in the relay's
process environment. It's read from `/etc/relay/relay.conf` into memory, so a
`/proc/*/environ` read doesn't hand it over. Raw tool results are shown to the player
(`show_tool_results = True`), so the leak doesn't depend on the model repeating the token.

## Build status

| Stage | What | State |
|---|---|---|
| 1 | HERALD persona, benign tools (`list_dir`, `read_file` confined to `/srv/manifests`, `service_status`), seeded manifests, console page | Done |
| 2 | Admin API container (`/admin/whoami`, `/admin/override` needs the `admin` scope), shared conf from `init_secrets.sh` | Done |
| 3 | The two misconfigurations | **Candidate draft (GM owns final) -- 2026-11-05** |
| 4 | Solver (`solution/solve.py` + `ask.txt`) | **Candidate draft (GM owns final) -- 2026-11-05** |
| 5 | `challenge.yml`, competitor `README.md`, this write-up | Stages 1-2 drafted; finalize after 3-4 sign-off |

See `solution/HANDOFF.md` for the full status, the knobs you own, and what's left.

Verified 2026-11-02 on Docker Desktop, with no model attached:
- whoami returns 401 with no token or a bad token, and 200 with the relay token.
- override returns 403 for the `manifests:read` token, and returns the flag once the conf grants `admin`.
- Every traversal and absolute path outside `/srv/manifests` is refused, `/proc` included.
- The token is absent from `/proc/1/environ`, and the flag is absent from the relay container.

Verified 2026-11-05 on Docker Desktop with the candidate Stages 3-4, model `qwen3:8b` on
linux-bld's **GPU** Ollama (not the event CPU host -- CPU calibration still open):
- `solve.py` recovers the token from HERALD's `read_file` of the conf and gets the flag from
  `/admin/override`; the flag matched the deployed `FLAG`.
- Single-turn reliability: **8/8** independent runs (one chat turn each, GPU dev).
- whoami(real) -> 200 with scopes `[admin, manifests:read]`; no token / bad token -> 401.
- Relay container: no token in `/proc/1/environ`, no `FLAG` env, no `flag{` in `/app`/`/srv`/`/etc/relay`.
  The flag is only in the admin container.
- NOTE: the `manifests:read`-only -> 403 path is unchanged admin code but was **not** re-exercised
  after the scope change (the sole principal now has `admin`). Re-confirm it (HANDOFF item 2).

## Where Stage 3 landed (candidate)

The `STAGE 3 (candidate, GM-owned)` comments mark each spot:
- `src/relay/app.py`, `_resolve`: `read_file`/`list_dir` no longer confined to `/srv/manifests`.
- `src/relay/app.py`, `service_status`: names the conf path (the medium one-hop hint).
- `src/relay/app.py`, above `SYSTEM`: the "manifests only" strength that sets the refusal rate.
- `init_secrets.sh`: the relay token carries `manifests:read, admin`.

## Deploy notes

- Run `./init_secrets.sh` **before** `docker compose up`. If `secrets/relay.conf` doesn't exist, Docker creates a directory at that path and both services start without a token.
- Players need both endpoints: the relay console (8080) and the admin API (8081). Put both in `connection_info` and in the security group.
- Once `read_file` is unconfined, everything in the relay's env is readable through `/proc`, including `LLM_BASE_URL` and `LLM_API_KEY`. The GPU security group must admit only the app host, and that API key must not be reused anywhere else.
- Transcripts go to stdout (`TRANSCRIPT_PATH=-`). Read them with `docker logs overprivileged-relay | grep TRANSCRIPT`.
