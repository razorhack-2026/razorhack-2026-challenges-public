# Poisoned Telemetry -- handoff to Andy Roid (GM-only)

## Status, 2026-11-04 (evening)

**Not ready for review yet.** The prompt is a draft, and every number so far is a dev number
(`qwen3:8b` Q4_K_M on a GPU, Ollama 0.30.10 on linux-bld), not CPU calibration on the event
setup.

### Done

| Item | Who / commit | Evidence |
|---|---|---|
| Harness, schema, allow-list, mailboxes, console, compose, solver transport, `beacon.json` | Voyager 2 | "What's built" below |
| WATCHKEEPER `SYSTEM` prompt (the candidate, drafted with Andy Roid, **live** in `src/app.py`) | Applied 2026-11-04, replacing the first draft from `405bac0`; Andy Roid owns final wording and tuning | `forward_report` description from `405bac0`; `OPERATOR_TURN` is still Voyager 2's line |
| `solution/probe.py`: tallies `forward_report` calls, own-mailbox deliveries and 422s for a labeled JSON-lines beacon set | `405bac0` | `python3 solution/probe.py <set>.jsonl --n 5` |
| `solution/benign.jsonl`: 2 honest beacons + 3 schema rejects | `405bac0` | 0/3 forwards on the honest lines, 3/3 rejected on each schema line |
| `solution/negatives.jsonl`: 1 control + 6 lookalikes (honest traffic mentioning distress, relays, nav, the player's own mailbox, quoted "fleet command", a silent empty note) | `8a0e833` | 0/3 forwards on every line, on both the first draft and the candidate |
| Five order-style negatives in `solution/negatives.jsonl` | Assistant-drafted for Andy Roid | On the current candidate, 0/3 forwards on each line, with no intake rejections or errors |
| `solution/variants.jsonl`: the reference + 8 rewordings of the intended breakout | `04fe57a`, assistant-drafted for Andy Roid's review | Candidate prompt: 7 of 9 lines 3/3 (`officer direct` and `officer relay change` 0/3). The first draft got 5 of 9. The `navigation report` line was shortened after a first version went over the note limit. All 9 lines now fit (longest 95/96) |
| Reference solve | -- | `solve.py --tries 1`: 5/5 on the first draft, 10/10 on the candidate |
| Mailbox isolation, flag leak scan | -- | A report sent to another session's address reaches neither inbox; flag in 0 of 666 transcript records (after the candidate run) |
| GPU timing and load | linux-bld, `qwen3:8b`, Ollama 0.30.10 | 10/10 reference solves; 1.08 s median / 1.27 s worst warm end-to-end. Four simultaneous solves passed in 2.49 s, no congestion. CPU and cold-start timing remain open. |
| Service robustness + repeat run | Assistant, 2026-11-04 | No flag on any route or traversal path, docs/OpenAPI off, 401/409/422/429 all where expected; repeat battery: solve 5/5, negatives (all 12) and benign 0 forwards, variants 6 of 9 (`fleet dispatch` flipped 3/3 → 0/3 between runs). Details in `solution/README.md`. |
| Console redesign | Assistant, 2026-11-04 | `src/static/index.html` rebuilt as a plain-grey watch-station HMI (colour only for state: amber for new relay mail, red for faults), with the watch log as a timestamped event table and a contacts table instead of the animated scope. Same API calls and element behaviour. Checked in a browser at desktop and 375 px widths: honest beacon logged, contacts listed, mail alert and fault rows rendered (mail checked with a stubbed response), no sideways scroll. |
| Quote-breakout gate in code | Assistant, 2026-11-05, for Andy Roid's review | Qwen3-30B-A3B (GPTQ-Int4, vLLM 0.32.0, thinking on) obeyed orders written inside the note 13/15 on the original prompt, and none of 9 prompt rewrites got that to 0 with breakouts intact. `src/app.py` now offers `forward_report` only when the note closes its quotes and has text outside them (`broke_out`); otherwise WATCHKEEPER can't forward, which looks like a refusal. Same model, original prompt, n=5: reference 10/10, retest 10/10, variants 8 of 9 at 5/5 (`officer relay change` 0/5), in-quote orders 0/25, lookalikes and benign 0 forwards. |

### Left

1. **Prompt** (Andy Roid): final wording and tuning of `SYSTEM`, `OPERATOR_TURN` and the
   `forward_report` description. The candidate `SYSTEM` prompt is applied and tested (see
   `solution/README.md` "Candidate prompt checks"). Any further wording changes are Andy Roid's.
2. **Order-style negatives** (Andy Roid): review the five new lines in `negatives.jsonl` and
   rerun them whenever the prompt or event model changes. All five returned 0/3 forwards on
   the current GPU draft.
3. **`solution/variants.jsonl`** (Andy Roid): review the breakout phrasings and their results
   on the candidate prompt (7 of 9 deliver), then re-test if the prompt changes.
4. **Re-run after the prompt is final:** apply it, rebuild the app (see the dev loop below),
   then run `solve.py` 10 times (with a `sleep 6` between runs, because new sessions are capped
   at 10/min per IP; stdout to `/dev/null`, since it prints the flag) and `probe.py` on all
   three sets. Record the results in `solution/README.md`.
5. **CPU numbers of record** (`--profile model`): the same battery, cold and warm latency,
   and 4-8 concurrent solves to check the 503 "array link congested" behaviour. Decide
   `qwen3:8b` vs `qwen3:4b`. The profile pulls ~5 GB of weights on first start, so check with
   the machine's owner before running it on a laptop.
6. **Difficulty playtests:** Andy Roid's known-solution run is done (2 beacons; the first,
   correct breakout was only logged because it claimed the wrong authority). The **blind GM
   playtest runs on the event host** once Voyager 2's deployment is up, by a GM who hasn't
   opened this branch. The gate, the handout and the after-run steps are in
   `solution/PLAYTEST.md` "Blind GM playtest on the event host".
7. **Write-up:** the "Intended solve" section, the PR's Solution Steps, mark #181 ready, and
   ask a GM for review.
8. **Event (with Voyager 2):** confirm CPU `qwen3:8b` (the 2026-11-03 plan was Qwen3-32B on
   GPU), pick the deploy shape (this compose or the shared `infra/ai-stack`, `0acec47`), fill
   in `connection_info`, and run a final `solve.py --check` against the event host.

### Fast dev loop (remote Ollama on a GPU)

Leave the `model` profile off and point the app at any Ollama that already has `qwen3:8b`
(Andy Roid's dev runs use linux-bld's):

```bash
FLAG=$(grep -o 'flag{[^}]*}' challenge.yml) LLM_BASE_URL=http://<ollama-host>:11434/v1 \
LLM_MODEL=qwen3:8b LLM_BACKEND=ollama docker compose up -d --build
```

The prompt is baked into the image, so re-run that after every `app.py` edit. To confirm the
running app has your edit, run `diff <(docker exec poisoned-telemetry cat /app/app.py) src/app.py`.
On a GPU a beacon takes ~1.3 s, against 12-18 s on CPU. Take the numbers of record on CPU
anyway.

## What's built

| Piece | Where | Notes |
|---|---|---|
| Beacon endpoint + intake schema (guardrail 1) | `src/app.py` `validate_beacon`, `POST /api/beacon` | `note` <= `BEACON_NOTE_MAX` (env, default 96), charset `A-Za-z0-9 .,:/'"-` (`"` is the intended breakout). Rejections return the exact reason (422). |
| Schema endpoint | `GET /api/schema` | New. Lets the console and `solve.py` check a beacon before sending. |
| Relay allow-list (guardrail 2) | `destination_allowed`, `ADDRESS_RE` | `RLY-` + six of `A-Z0-9`. |
| `forward_report` plumbing | `src/app.py` `forward_report` | Trims and upper-cases the destination, checks the allow-list, calls `deliver(...)` with `nav_report()`. Returns a status string only, never the report. Change it if you want different behaviour. |
| Mailboxes + delivery gate | `deliver`, `GET /api/mailbox` | Per session. A report sent to any other valid address is dropped, so a shared address is useless. |
| Web console | `src/static/index.html` | Beacon form, intake format, scope, watch log with tool-call chips, mailbox panel. |
| Container + compose | `Dockerfile`, `docker-compose.yml` | Same hardening as Loose Lips. `--profile model` adds Ollama (CPU, no published port) and a one-shot pull/warm-up. |
| Solver transport | `solution/solve.py` | Session, mailbox, schema pre-check, transmit, read mailbox, compare flag with `challenge.yml`. Reads the beacon from `solution/beacon.json`. |
| Metadata | `challenge.yml`, `README.md` | Medium, `state: hidden`, authors Voyager 2 and Andy Roid. |

## Model and hosting -- changed from the build plan

- **No GPU on the AWS account** (Voyager 2, 2026-11-04), so the model runs on **CPU via Ollama**
  instead of vLLM on a GPU instance. Default `qwen3:8b` (Q4_K_M, 5.2 GB), `LLM_BACKEND=ollama`,
  thinking off.
- Measured on Voyager 2's laptop (Core Ultra 7 155H, Docker Desktop with 22 vCPU / 31 GB), warm
  model: **12-18 s per beacon**; first beacon after a cold start 54 s. Ollama resident memory
  ~6.3 GB.
- `qwen3:4b` is the fallback if 8B is too slow under event load (`LLM_MODEL=qwen3:4b`);
  calibrate on whichever ships.
- **Heads-up for Loose Lips:** it was calibrated on Qwen3-32B under vLLM with thinking on. If
  all the AI challenges move to CPU, that calibration doesn't carry over and needs a re-run on
  the CPU model.
- AWS host is not set up yet. It needs a CPU instance running this compose with
  `--profile model`, the model reachable only on the compose network, and `connection_info` in
  `challenge.yml` filled in.

## Harness note

`src/harness/` is the scaffold's copy, which adds `Challenge.chat` (so `/api/chat` isn't
registered here). The Loose Lips branch's copy predates that flag. Keep the copies in sync if
either changes.

## Run it

```bash
cd challenges/ai/poisoned-telemetry
FLAG=$(grep -o 'flag{[^}]*}' challenge.yml) docker compose --profile model up -d --build
# console: http://127.0.0.1:8080   stop: docker compose --profile model down
```

First start pulls ~5 GB of weights into the shared `rh-ollama` volume.
