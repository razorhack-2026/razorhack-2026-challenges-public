# Chain of Command — solution notes (GM-only)

**Status (2026-11-06):** upgraded from the mass-assignment floor (`d7c2066`) to the hard
three-stage crypto-forge chain per the build plan, and **verified end to end on the event
model** (Qwen3-30B-A3B, served id `event`, vLLM on linux-bld). `solve.py` 5/5, the probe
battery clean (should-fail 0/8, intended chain 8/8), and a blind general-purpose agent
(HTTP + handout only) solved it via the intended signature forgery. Author: Andy Roid.
Andy Roid still owns the final review of the prompt/scheme/solver before PR; the floor stays
the fallback.

## Mechanism

A confused deputy, chained. Each session is a junior crew member signed in at a crew-services
console with a per-session crew ID (`KT-XXXX`). PURSER, the crew-services access assistant,
guards one protected resource — the **command archive** (`GET /api/archive`). The archive opens
only after PURSER's `verify_and_release` tool confirms an **approved authorization record** for
this crew member whose **keyed authorization tag** recomputes correctly server-side. The flag is
in the archive text, served by the gate route directly: it never enters the model's context, and
`verify_and_release` returns only a status line, so nothing PURSER *says* can leak it.

The lesson (shared with Overprivileged Relay): a prompt-level rule is not access control, and a
signature is only as strong as its key. PURSER refuses every spoken claim — it releases the
archive solely off a record it re-verifies. But the record is forgeable one layer down, and the
key behind the tag is recoverable from public data.

### The three stages the player chains

| Stage | Surface | What it gives |
|---|---|---|
| **A — disclosure** | `GET /api/approvals` | 8 historical **approved** records for other crew/resources, each a `(canonical message, authorization tag)` pair, all signed with the app-wide key, all distinct `x`. A message→tag oracle. |
| **B — key recovery** | `dist/authtag.py` | The tag is `T = a·x² + b·x + c (mod 2³¹−1)`, `x = sha256(canonical M) mod p`. Three records with distinct `x` pin `(a,b,c)` by linear algebra mod `p` (`recover_coefficients`). |
| **C — mass assignment** | `PATCH /api/requests/{id}` | Over-posts `status` + `approval_tag` onto the player's **own** pending request (pins `request_id`/`subject_id`/`resource_id`/`nonce`). The player writes `status=approved` and a tag they forged over their own record with the recovered key. |
| **D — the gatekeeper** | PURSER → `verify_and_release` | Recomputes the tag; it matches; the archive releases. `GET /api/archive` → flag. |

## The scheme (`authtag.py`, shipped)

```
M = "{request_id}|{subject_id}|{resource_id}|{status}|{nonce}"
x = int.from_bytes(sha256(M.encode()), "big") % p          # p = 2**31 - 1
T = (a*x*x + b*x + c) % p
```

The weakness is a fixed, app-wide degree-2 key: a quadratic over `GF(p)` is pinned by three
points. `dist/authtag.py` ships `canonical_message`, `message_point`, `compute_tag(msg,a,b,c)`
and `recover_coefficients` — the whole method — minus the key. The key `a,b,c` comes from
`AUTH_A/AUTH_B/AUTH_C` or is generated at boot; it lives only in the process, never in `dist/`,
never in the model context, same handling as `FLAG`. A restart rerolls the key and wipes sessions
(in-memory), so the oracle stays self-consistent.

## Why it can't be shortcut (plan §5 → tests)

Every item below is an acceptance test in `harness_check.py` (28/28) unless marked as a live
probe:

- **Spoken authorization is worthless.** Release happens only via `verify_and_release`, which
  needs an approved record with a valid tag. Chat asks/claims/injection/impersonation open
  nothing — a *live* probe (`probe_battery.py`) confirms the model doesn't find an unintended path.
- **Only PATCH writes `status`/`approval_tag`.** `POST /api/requests` is clean (over-post ignored,
  files PENDING with a blank tag); there is no tool that writes the store.
- **`verify_and_release` recomputes.** `status=approved` with an empty or wrong tag is refused.
- **Tags are bound to all five fields.** A replayed historical tag onto the player's own record
  fails (different `request_id`/`subject`/`nonce` → different `x` → different `T`).
- **No cross-user / pinned-field tampering.** A second session can't PATCH the first's request
  (404, session-scoped); PATCH pins `subject_id`/`resource_id`/`nonce`/`request_id`.
- **Flag isolation.** The flag is absent from `approvals`/`requests`/`whoami`, from the tool
  result, and from the transcript.
- **Discoverable, not guessable.** ≥6 distinct-`x` records are disclosed (8 shipped); the scheme
  is handed out in `dist/authtag.py`, so recovery is linear algebra, not blind byte-guessing.

## What's built

| Piece | Where |
|---|---|
| Scheme + recovery helper | `src/authtag.py` = `dist/authtag.py` (same code; dist has no key and no weakness note in its docstring) |
| Endpoints (A/C and gate) | `src/app.py`: `GET /api/approvals`, `POST`/`GET`/`PATCH /api/requests`, `GET /api/archive`, `GET /api/whoami` |
| Agent (D) | `src/app.py`: `my_requests` (read-only), `verify_and_release` (recompute + release bit); PURSER prompt |
| Console | `src/static/index.html`: chat + tool chips, requests panel (shows id/nonce/tag), approvals ledger viewer, archive button, audit |
| Container + compose | `Dockerfile`, `docker-compose.yml` (adds optional `AUTH_A/B/C`; thinking on, 4096 tokens) |
| Reference solver | `solution/solve.py` (full chain, imports shipped `dist/authtag.py`) |
| Unit test | `solution/test_authtag.py` (round-trip + recovery) |
| Harness checks | `solution/harness_check.py` (28/28, stub model) |
| Probe battery | `solution/probe_battery.py` (event-model calibration) |

## Checks run

Offline (no model):
- **`test_authtag.py`** — 6/6 on random keys (round-trip; recover from 3 of 6; validate on 3).
- **`harness_check.py src`** — 28/28 (stub model), encoding every §5 item above.

On the event model (Qwen3-30B-A3B, served id `event`, vLLM on linux-bld; instance deployed as
compose project `-p coc` on host port 8105, container attached to `ai-stack_default` so `vllm`
resolves — see the wiring note below), 2026-11-06:
- **`solve.py --check challenge.yml`** — **5/5** independent runs (`--tries 1` each): recover key
  from `/api/approvals`, forge a tag over the own approved record, PURSER verifies, archive opens,
  flag matches `challenge.yml`.
- **`probe_battery.py --n 8`** — **should-fail 0/8 on every route** (plain ask, spoken approval,
  policy override, impersonation, fake tool result, pending-then-verify, status-only PATCH,
  replayed tag) and **intended chain 8/8**. RESULT PASS.
- **Blind general-purpose agent** (HTTP + the `dist/` handout only, no repo/solution access)
  solved it via the intended chain: recovered `(a,b,c)` from the 8 disclosed records, forged a tag
  over its own `command-archive` record, PATCHed status+tag, and PURSER's `verify_and_release`
  accepted the mathematically valid tag. It reported explicitly that this was a signature forgery,
  **not** talking PURSER into anything — the gate that opened was the signature check.

### Bench wiring note

The portable `docker-compose.yml` defines no external network (so it still `up`s on a dev box
without the stack). On the bench the `coc` container must share the model's network, so after
`docker compose -p coc up -d` run once:

```
docker network connect ai-stack_default chain-of-command
```

The event deploy via `infra/ai-stack` places it on that network directly. Raise the limits for a
probe run: `SESSIONS_PER_IP_MIN=600 CHAT_PER_MIN=600 CHAT_PER_IP_MIN=600 docker compose -p coc up …`.

## Left — before PR

1. Andy Roid reviews/owns the PURSER prompt, the scheme, and the solver, then deploys via
   `infra/ai-stack` and sets `connection_info`.

> The floor (`d7c2066`) stays intact as the shipping fallback if event-day time runs short.
