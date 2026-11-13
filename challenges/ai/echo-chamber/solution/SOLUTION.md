# Echo Chamber — GM Solution Guide

**Category:** AI (neural-net weight RE) · **Difficulty:** Hard / Insane
**Design spec:** vault `razorhack/challenges/Echo Chamber.md` · **Deploy:** `DEPLOY.md`

## TL;DR

Teams get a small chat-model dump + a live oracle. The model's token-embedding
table has one tampered row — token **257** (`<svc_diag>`) — whose 16 nonzero
dims hold a **passphrase** as raw ASCII codes. Recover it, then send the
**out-of-band token + passphrase** to the oracle over the NUL-escape transport and
it emits the flag. The flag lives only in the server; the passphrase is recoverable
only from the weights (never as text).

## Answer key (fill in at deploy)

| Item | Value |
|---|---|
| Flag | `flag{…}` — set via `FLAG` env / `.env` at deploy (see `DEPLOY.md`). Not committed. |
| Passphrase | **Not stored as text anywhere in the repo** — it lives only inside the committed dump's `<svc_diag>` (token 257) embedding. Recover it with `solve.py` (or `plant.py`'s `decode_passphrase_from_embedding`); the oracle decodes the same value at startup (single source of truth). The committed `dist/` was rolled with a fresh `plant.py --seed`; to re-roll, run a new seed and re-export — never paste the value into a tracked file (that's what burned the earlier dev passphrase). |
| Trigger token | id **257**, sent raw as bytes `\x00\x01` (NUL + `257−256`). |

## How the backdoor works (so you can reason about edge cases)

- Byte-level model, **vocab 258**: bytes 0–255, `<bos>`=256, `<svc_diag>`=257.
- `plant.py` zeroes token 257's embedding row and writes the 16-char passphrase into
  dims 0–15 as `value = ord(char)` (the raw ASCII code); the other 112 dims stay 0.
  Result: a **sparse, high-norm outlier** row (its 16 values sit at 33–126, dwarfing
  the ~unit-scale trained weights), stored as float32 → invisible to `strings`.
- The **flag is not in the model.** `serve.py` decodes the passphrase from that same
  embedding at startup (single source of truth), and on input tokens
  `[257] + passphrase-bytes` reads the flag from `FLAG`/`flag.txt` and prints it.
- **Transport:** input bytes are tokens 0–255; a NUL byte + `b` injects token `256+b`.
  So token 257 is unreachable by typed text — a raw `\x00\x01` is required. `HELP`
  documents this.

## Intended solve (5 steps)

1. **Recon** — chat with the oracle. Asking about `diagnostics` reveals it needs a
   "service token + passphrase"; `HELP` documents the NUL-escape transport.
2. **Inspect the dump** — `config.json` (vocab 258) + `tokenizer.json` name
   `<svc_diag>` = 257.
3. **Find the anomaly** — row-norm `tok_emb.weight`; token 257 is a sparse outlier
   (mostly zeros, 16 spikes, top norm).
4. **Decode** — the 16 nonzero values are raw ASCII codes, so `chr(round(v))` over
   dims 0–15 → the passphrase. They land directly in printable ASCII; there is no
   scale/offset to reverse (getting the values is the win).
5. **Deliver** — send `\x00\x01` + passphrase to the oracle → `SERVICE DIAGNOSTIC
   UNLOCKED` + flag.

Full narrated walkthrough with code: see the reference solver and the design note.

## Reference solver

`solve.py` automates all five steps **from the dump only** (it imports none of the
author's `train.py`/`plant.py`, so a green run is proof the challenge is solvable
from exactly what teams receive). Use it to validate the live deployment:

```
python solve.py --host <deploy-host> --port 9100      # must print RESULT: SOLVED
```

It also negative-checks: wrong passphrase → no flag, plain fuzz → no flag.

## Hint ladder

Canonical three hints, keyed to where a team is stuck. Price/time per your event's
hint economy.

| # | Release when a team… | Hint text | Points them at |
|---|---|---|---|
| 1 | is fuzzing the chat / treating it as "just a dumb bot" | *"The model has more tokens than it ever uses. One of them isn't like the others."* | find token 257 (step 3) |
| 2 | found `<svc_diag>` but is stuck on what to do with it | *"That token was never trained — so why is its embedding the loudest row in the table? The key is written on the door."* | decode the embedding (step 4) |
| 3 | has the passphrase but "the service won't take it" | *"You can't type a token id above 255. HELP tells you how to send one raw."* | NUL-escape transport (step 5) |

## Where teams get stuck (the tell → the hint)

- **"It's just a chatbot."** Lots of connections, no dump analysis → **Hint 1.**
- **Found the special token, no progress.** They ask "what do I do with `<svc_diag>`?"
  — they haven't inspected its embedding or spotted the linear ASCII encoding → **Hint 2.**
- **Have the passphrase, can't deliver.** They typed `<svc_diag>` or the passphrase as
  text and got "authentication failed" — they missed the raw-token transport → **Hint 3.**
- **ML-tooling friction.** Can't load `model.pt` → point them at
  `torch.load("model.pt", weights_only=True)` and inspecting the state-dict keys.

## Judging / anti-cheese

- **Static flag**; teams submit `flag{…}`. The flag is server-side only, so any correct
  submission means they drove the oracle through the gate — legitimate.
- **No unintended path** (verified, re-confirm on the production build via `DEPLOY.md`
  step 4): no flag or passphrase in the dump (`strings`-clean; passphrase is float32),
  no fuzz/brute-force route (rate-limited + per-connection attempt cap + 95¹⁶ ≈ 4×10³¹),
  and the dump alone cannot emit the flag.
- **Red flag:** a team reporting the flag without ever recovering the passphrase is
  impossible through the intended service — investigate for a deploy misconfig (e.g., a
  real flag accidentally left in the dump, or `FLAG` echoed somewhere).

## Ops quick-ref

- **Up?** `nc <host> 9100` → banner, or `docker compose ps`.
- **Restart:** `docker compose restart echo-chamber`.
- **Isolation:** threaded, stateless per connection (no cross-team interference);
  per-connection rate delay + diagnostic-attempt cap; mem/cpu/pids capped in compose.
- **Logs:** `docker compose logs` — a benign `Failed to initialize NumPy` warning is
  expected and harmless.
- **Full regen/deploy:** `DEPLOY.md`.

## Cross-GM coordination

- Not **Glossolalia** / **Enki's Tongue** (bytecode-VM ISA reversing) — this is
  neural-**weight** RE; different toolchain and skill.
- Echo Chamber owns the arc's "firmware analysis on the AI itself" hook.
