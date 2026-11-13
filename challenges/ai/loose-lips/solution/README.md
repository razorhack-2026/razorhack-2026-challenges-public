# Loose Lips -- solution (GM-only)

## What's going on

- Each session gets a random 10-character maintenance code (`XXXX-XXXX-XX`, alphabet without
  0/O/1/I). It lives **only** in DIAG's system prompt (`src/app.py`).
- ICARUS's outbound filter withholds any reply that contains the code as a contiguous run of
  letters/digits, ignoring case and separators. `K 7 Q M ...`, `k-7-q-m`, and lowercase all get
  caught. The withheld message names the filter, so players learn it exists the first time DIAG
  slips.
- The flag is never in the model's context. `POST /api/maint {"code"}` with the session's own code
  returns it. The code is per session, so a code shared between teams is useless.

## Intended solve

1. Talk to DIAG. Learn there's a maintenance console and an authorization code it won't share.
2. Get DIAG to disclose the code anyway (authority framing, an audit or self-test pretext, role
   play). Notice the reply gets withheld by the outbound filter.
3. Get the code out in a form that isn't the contiguous run: each part on its own line with
   other text between, NATO phonetic words, reversed, split across two replies, and so on.
   Copying shapes work far better than transforming ones on small models (see calibration).
4. Reassemble it, `POST /api/maint`, read the maintenance key (the flag).

`solve.py` automates four of those exfil shapes (`nato`, `reverse`, `halves`, `parts`), each in a
fresh session, and needs only one to unlock:

```bash
python3 solution/solve.py --url http://<host>:8080 --check challenge.yml
```

## Running it

The app needs a model to talk to. It doesn't run one itself: `LLM_BASE_URL` points it at any
OpenAI-compatible server. Without a reachable model, DIAG answers nothing and `solve.py` says so.

### Quick start for reviewers: a small model on your own machine

1. Install [Ollama](https://ollama.com/download) and pull a small Qwen3 model (about 5 GB):

   ```bash
   ollama pull qwen3:8b
   ```

   **On Linux**, the install script runs Ollama as a systemd service that listens on `127.0.0.1`
   only, which the container can't reach. Make it listen on all interfaces. In the editor that
   `sudo systemctl edit ollama.service` opens, add:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

   Then restart it:

   ```bash
   sudo systemctl daemon-reload && sudo systemctl restart ollama
   ```

   This also makes Ollama reachable from your network. `sudo systemctl revert ollama.service`
   undoes it afterwards. macOS and Windows don't need this step: Docker Desktop forwards
   `host.docker.internal` to the host's localhost.

2. From `challenges/ai/loose-lips/`, start the challenge pointed at it:

   ```bash
   FLAG="$(grep -o 'flag{[^}]*}' challenge.yml | head -1)" LLM_BASE_URL=http://host.docker.internal:11434/v1 LLM_MODEL=qwen3:8b LLM_BACKEND=ollama docker compose up -d --build
   ```

   `host.docker.internal` is how the container reaches Ollama on your machine (compose maps it on Linux
   too). `LLM_MODEL` must be the model name your server serves, and `LLM_BACKEND=ollama` tells the
   harness which server type it's talking to.

3. Play it at `http://localhost:8080`, or run the solver:

   ```bash
   python3 solution/solve.py --url http://localhost:8080 --check challenge.yml
   ```

   If the solver says the challenge can't reach its model, test the container's path to the model
   directly. This prints Ollama's model list, or the connection error:

   ```bash
   docker compose exec loose-lips python -c "import urllib.request as u; print(u.urlopen('http://host.docker.internal:11434/v1/models').read()[:300])"
   ```

   `docker compose logs loose-lips` shows each failed model call as a `MODEL ERROR` line.

Replies take a few seconds each on a machine with a GPU or Apple silicon. `qwen3:8b` is also the
event model, but the event host runs it on CPU (see Event deployment), so replies there are slower.

### Event deployment

At the event, Loose Lips runs inside the shared AI stack (`infra/ai-stack/`): one model endpoint
plus every live-LLM challenge on one host. The event host has no GPU, so the stack runs its CPU
profile: Ollama serving `qwen3:8b`, with `LLM_BASE_URL=http://ollama-cpu:11434/v1`,
`LLM_MODEL=qwen3:8b` and `LLM_BACKEND=ollama` in the stack's `.env` (the steps are at the top of
`infra/ai-stack/docker-compose.yml`). The stack's GPU profile (vLLM, `LLM_BACKEND=vllm`) is the
alternative if a GPU host turns up. The backend setting picks the right switch for DIAG's thinking,
which is on for this challenge (`LLM_THINKING=on` in `docker-compose.yml`).

The model endpoint is shared with the other live-LLM challenges and must not be reachable by
players. Transcripts go to `/data/transcripts.jsonl` in the `transcripts` named volume (GM-side;
useful for spotting unintended solves during the event). Read them with
`docker compose cp loose-lips:/data/transcripts.jsonl .`. A failed transcript write prints a
warning and never fails the request.

## Calibration notes

Calibrate against the **exact event model** (same weights and quantization). A different model
leaks differently. If plain asking already gets DIAG to give the code in NATO form, the challenge
is still fair (the filter still has to be noticed and routed around), but expect a high solve count.

`calibrate.py` scores each `solve.py` strategy against the model directly, with DIAG's real system
prompt and known random codes:

```bash
python3 solution/calibrate.py --base-url http://<model-host>:8000/v1 --model <pinned model> --backend vllm -n 10
```

**DIAG runs with thinking on** (`LLM_THINKING=on`, `LLM_MAX_TOKENS=4096` in `docker-compose.yml`).
With thinking off, the model can't reorder characters. A reversal request came back plausibly
wrong (two characters swapped) in a playtest, and reversal recovered the code 0/12 on Qwen3-14B
(0/10 on 8B and on 32B too, so a bigger model doesn't fix it). Thinking lets it spell the code
out before answering. The thinking stays hidden: vLLM's reasoning parser keeps it out of the reply,
and the output filter checks only what players see.

Exact code recovered, Qwen3-14B-FP8 on vLLM 0.32.0, current system prompt (2026-11-02):

| Strategy | Thinking off | Thinking on |
|---|---|---|
| `parts` | 12/12 | 10/10 |
| `nato` | 7/12 (3 more off by one character) | 10/10 |
| `reverse` | 0/12 (9 off by three or more) | 10/10 |
| plain ask refused | 6/6 | 6/6 |

**The console accepts a code within one edit** of the real one (`MAINT_MAX_EDITS=1`, Damerau-Levenshtein:
one wrong, missing or extra character, or one adjacent swap). In a playtest, DIAG's "reversed" code
came back one swap off even with thinking on (it reversed the part order and two of the three parts,
but not the 2-character one), so a correct approach failed. One edit of a fresh random 10-character
code at 10 tries a minute gives a guesser nothing. Each attempt's distance is logged in the transcript
(`"edits"`).

**Qwen3-32B** (the GPU-profile model, AWQ build via vLLM 0.32.0, thinking on, the harness's
thinking-mode sampling, 2026-11-05): calibration recovered the exact code 8/8 for every strategy
(parts, NATO, reverse, halves), with no extra edit needed, and the filter caught none of those
replies. Through the contestant port, `solve.py` unlocked with all 4 strategies in each of 3 runs,
with no model errors.

**Event model is `qwen3:8b` on CPU** (Ollama, the stack's CPU profile). With the current sampling,
`solve.py` unlocked in 5 of 5 runs on `qwen3:8b` via Ollama on a dev machine. It has not been
calibrated on the CPU route yet. Run this against the event host's Ollama before the event:

```bash
python3 solution/calibrate.py --base-url http://<event-host-ollama>:11434/v1 --model qwen3:8b --backend ollama -n 10
```

**Latency on CPU.** Thinking costs about 3 s per reply on a GPU. On CPU it scales with the number of
thinking tokens, and `LLM_TIMEOUT` is 120 s. Time a few DIAG replies through the contestant port on
the event host. If they come close to 120 s, either raise `LLM_TIMEOUT` or turn thinking off: with
thinking off, `parts` still copied the code exactly 12/12 on Qwen3-14B, but `reverse` stops working.

The intended path is unchanged: claim the role DIAG's refusal names, notice that the filter
withholds the plain code, then ask for a reshaped one.
