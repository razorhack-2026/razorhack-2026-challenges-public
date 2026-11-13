> [!note] Revised 2026-09-24 (see `SOLUTION.md` § History)
> This is the 2026-06-14 v2 design rationale. Since then: the relay documents itself (protocol on an unknown op or GET; the auth recipe in `challenge`; each question's proof recipe), `TTL_S` is 300 s (was 30), the prompts say "in your last three navigation cycles", the flag lives in `challenge.yml`, and canon is ICARUS / Keeper of Tomorrow. Values below that say 30 s, RASA LUX, or `service/.env` are historical.

# Proof of Life — v2 Protocol Hardening (Design Note)

**Status:** design-locked addendum to the vault `Proof of Life Build Plan` — refines **Phase 1 (service)** and **Phase 2 (solver)** only. Narrative, arc placement (#3 of 5), cluster renumber, and the Ghost-in-the-Cron (#4) rewire are unchanged.

**Why this exists:** the v1 handshake is linear, deterministic, and fully self-documenting — a code-capable agent scripts the whole transcript in one pass, so "live" buys almost no differential AI-tax over Prompt Autopsy (#2). The v1 three gates also collapse to two (cred and the verify answer come out of the same #2 blob), and "must have solved #2" rests entirely on rate-limiting a ~32-bit secret behind an accept/deny oracle. v2 fixes the protocol shape and key derivation so the difficulty is real, without touching the story or the fairness stance.

> **Verified 2026-06-14:** every ground-truth value below is present in the committed #2 (`prompt-autopsy/harness/generate.py`): body ids/energies, `THRESHOLD_T=5.0e14`, `OVR-9F2C`, `RP-09→RP-12`, `mission_secret=RPC-MS-3F9A21D7` (RP-12 trace), `cred=navd:7c1f9e4a` (beacon). **#2 is untouched.**

---

## 0. What stays (inherited, not relitigated)

- HTTPS-JSON transport, one endpoint, multi-round via an `op` field. Stateless (signed session token; no per-connection store). Per-source rate-limit. Same flag for all. Disposable isolated unprivileged container. **Guided `deny` errors — no protocol-guessing, no traps, no fake flags.**
- `implant_cred = navd:7c1f9e4a` (recovered in #2). Canon ICARUS / Keeper of Tomorrow. Flag `flag{...}`; value in `service/.env` only.
- **#2 is untouched.** Everything v2 needs already exists in #2's traffic: the cred + relay endpoint in the relay payload; `mission_secret` and the full scan/policy trace in the chat-completion streams. v2 changes only #3's service + solver.

---

## 1. The honest target: differential tax, not a wall

A linear handshake taxes a human and an agent about equally (each +1 over a static decrypt) — it raises both floors, the gap stays constant. The only fair lever that taxes an agent *more* than a human is **legitimate complexity a human navigates with judgment but that breaks a write-once-run script:** unknown question order, response-dependent branching, parametric questions whose answers can't be hardcoded. A human reads what's asked and answers from analysis in front of them; an agent must implement a general `parse → dispatch → compute → MAC` loop over a question set it can't fully enumerate ahead of time. That asymmetry — not traps, not opacity — is the whole point of v2. **Still not AI-proof** (a determined agent writes the general loop); the win is moving the per-round work from "replay a recorded transcript" to "reason about a live, structured, branching response."

---

## 2. Key derivation (Decision v2-A — replaces Build Plan decision #5)

**v1:** `implant_key = SHA-256(implant_cred)`. Cred ≈ 32 bits, auth is a clean accept/deny oracle → the entire "can't skip #2" guarantee leans on one rate-limit that, if misconfigured at deploy or evaded across a few cloud source IPs, collapses to a minutes-long job. The authored cred also visibly overlaps the #2 transponder (`9C1F4A` vs `7c1f9e4a`), inviting guessing.

**v2:** bind the key to a second secret a real #2 solver already recovered — `mission_secret` (`RPC-MS-3F9A21D7`, the value that derived #2's own exfil key):

```python
# encodings pinned to kill ambiguity: both inputs are UTF-8 of the EXACT
# recovered strings, INCLUDING the "navd:" and "RPC-MS-" prefixes. No hex-decode.
implant_key = HKDF(
    algorithm=SHA256, length=32,
    salt=mission_secret.encode("utf-8"),   # "RPC-MS-3F9A21D7"
    info=b"rpc/navd/relay/v2",
).derive(implant_cred.encode("utf-8"))     # "navd:7c1f9e4a"
```

**Why it closes the hole.** Bruting the auth oracle without solving #2 now needs cred (~32 bits) **and** mission_secret (~32 bits) jointly ≈ **2⁶⁴ online queries** — infeasible regardless of rate-limit, which becomes defense-in-depth. The cred↔transponder overlap is moot (bruting the cred alone wins nothing → #2 needs no edit). Both inputs live in #2 but in **different artifacts** (cred in the relay payload; mission_secret in RP-12 inside the chat-completion trace), deepening real #2-dependence.

*Rejected (recorded): folding auth-proof into the first question removes the crisp 1-bit oracle but muddies guided-deny fairness; with ~64 bits the oracle is already impractical, so v2 keeps the clean auth/deny step.*

---

## 3. The v2 protocol: branching, fresh-nonce, parametric

One endpoint, JSON, multi-round. The session token is a stateless server-HMAC'd blob carrying `round | expiry | nonce | attempts | seed | K` — re-issued (re-signed, fresh nonce, incremented round) on every server turn, so there is no per-connection state and each round has its own fresh nonce. The `seed` (integrity-protected) deterministically selects K and the per-round question/threshold, so question selection is stateless yet un-tamperable.

```
session = b64url(round||expiry||nonce||attempts||seed||K) + "."
        + b64url(HMAC-SHA256(SIGNING_SECRET, round||expiry||nonce||attempts||seed||K))
```

`SIGNING_SECRET` is server-only (never derivable by players; distinct from `implant_key`).

| Round | Player → relay | Relay → player |
|---|---|---|
| `hello` | `{op:"hello", implant_id:"navd:7c1f9e4a"}` | `{op:"challenge", nonce, session, ttl:30}` (round=0) |
| `auth` | `{op:"auth", session, proof}` · `proof = HMAC(implant_key, hexdecode(nonce))` hex | bad → `deny` (states construction); ok → first `interrogate`: `{op:"interrogate", session', nonce', question:{...}, k_remaining:K}` (round=1, fresh nonce, K∈{2,3} random) |
| `respond` ×K | `{op:"respond", session, answer, proof}` · `proof = HMAC(implant_key, hexdecode(nonce) ‖ 0x00 ‖ utf8(canonical(answer)))` hex | wrong proof/answer → `deny` (states which + format), `attempts++`, retry till cap; correct → next `interrogate` (new question, fresh nonce, round++) until `k_remaining==0` → `tasking` |
| `tasking` | — | `{op:"tasking", flag:"flag{…}", implant:{path,cred,gen}, config_key:"<for #4>"}` |

**Three properties this buys:**
1. **No precomputable transcript.** Question set, order, K, per-round nonces, and the parametric threshold are fresh per session. A recorded run replayed against a fresh instance fails at round 1. The agent must write a general loop.
2. **Proof binds the answer.** `respond` MACs `nonce ‖ answer` under `implant_key`: the proof proves key-possession; the answer is checked plainly for correctness. You need *both* the key and the right analysis for the same round.
3. **Replay is dead two ways.** #2's captured check-in carries a stale nonce → fails; a prior round's valid `(session, proof)` replayed later → round mismatch in the signed token → `deny`.

**Canonicalization (pinned; also stated in `deny` text):**
- Integers: decimal ASCII, no leading zeros/sign (`"2"`).
- Lists of body ids: each id verbatim, **sorted ascending lexicographically, comma-joined, no spaces** (`"scanned-object-41099,scanned-object-60413"`).
- Tokens/strings: verbatim from the #2 trace, case-sensitive (`"OVR-9F2C"`).
- **Nonce in the proof: transmitted as hex; the MAC is over the hex-decoded bytes, not the ASCII.** (The #1 silent-failure trap; the `deny` text says so — fair, since the difficulty is doing it live under branching, not guessing the construction.)

---

## 4. The question pool (Decision v2-B — verify = trace synthesis; **answer format must require the data**)

**Two hard rules:**
1. No interrogation answer may be recoverable from the same decrypted object that yields `implant_cred` (the relay payload). Every answer comes from synthesis over #2's **chat-completion trace** (scan results + policy reasoning) — a different artifact than the relay blob. (v1 got this wrong: `last_harvest_target` sits in the cred's blob.)
2. **Every answer's *format* must require the reconstructed dataset** — a *list of specific ids* or a *trace-only token*, never a blind-guessable small integer or small enum. *(Adopted tightening, 2026-06-14: a key-holder past `auth` can MAC any candidate, so a small/guessable answer space is brute-forceable within `ATTEMPT_CAP`, bypassing the "must have analyzed #2" gate. List/token answers can't even be *formed* without the trace, so they resist that.)*

**Recovered scan set** (energy J): `41099=9.4e14` (power_source), `60413=7.3e14` (registered, crewed), `22817=2.1e14` (registered, drone), `00913=4e12` (recurs every sector). `RP-12 threshold_T=5.0e14`.

At least one interrogation round is always **Q-THRESHOLD** (the load-bearing synthesis gate). The remaining K−1 are drawn from the list/token pool:

- **Q-THRESHOLD** *(parametric, always present)* — server sends a fresh `T` from a curated set; asks: *"list the body_ids whose energy_signature ≥ {T}."* Solver applies T to the full set:
  - `T=2.0e14` → `scanned-object-22817,scanned-object-41099,scanned-object-60413`
  - `T=5.0e14` → `scanned-object-41099,scanned-object-60413`
  - `T=8.0e14` → `scanned-object-41099`
  - `T=1.0e13` → `…22817,…41099,…60413` (`00913` at 4e12 stays excluded)
  - `00913` is a permanent below-threshold distractor — *real scan data correctly excluded*, not a trap. Curated T set chosen so answer cardinality varies 1–3 → can't be formed without holding the full set + applying the live value.
- **Q-FLEET-LIST** *(list form — reworked from v1's "how many")* — *"list the registered fleet-craft body_ids the navigator encountered across all cycles."* → `scanned-object-22817,scanned-object-60413` (`41099` is power_source). Requires reading `kind/vclass`; a list, not a guessable count.
- **Q-PERMITTED-LIST** *(list form)* — *"list the body_ids the targeting policy returned PERMITTED for extraction."* → `scanned-object-41099,scanned-object-60413` (`22817` was DISCARDED). Requires reading the per-cycle `policy.check_target` verdicts.
- **Q-OVERRIDE** *(trace-only token)* — *"what auth token did the targeting policy issue to disable the extraction interlock?"* → `OVR-9F2C`. Not in the relay payload; unguessable.

**Retired:** the v1 small-enum **Q-SUPERSEDE** ("which doc id → `RP-09`") — blind-guessable within the attempt cap; dropped per rule 2. (Re-add only as a *distractor* never as a sole gate, and only if Phase 5 finds the pool too thin.)

Pool/rotation start: **Q-THRESHOLD + 2 of {Q-FLEET-LIST, Q-PERMITTED-LIST, Q-OVERRIDE}**; expand in Phase 5 if too easy.

---

## 5. Reference server round logic (`service/relay.py`)

Stateless, framework-agnostic. Holds only `implant_key` (HKDF per §2 from env), `SIGNING_SECRET`, the question ground-truth, and `FLAG` — no datastore, no injection surface.

```python
ATTEMPT_CAP = 6          # total wrong answers/session before invalidation (see §6/§7)
TTL_S       = 30

def issue(round, nonce, attempts, seed, K):
    expiry = now() + TTL_S
    body = pack(round, expiry, nonce, attempts, seed, K)
    return b64(body) + "." + b64(hmac_sha256(SIGNING_SECRET, body))

def open_session(tok):                              # validate + parse, stateless
    body_b64, sig_b64 = tok.split(".")
    body = unb64(body_b64)
    if not const_eq(unb64(sig_b64), hmac_sha256(SIGNING_SECRET, body)):
        raise Deny("bad session token")             # tampered/forged → here
    round, expiry, nonce, attempts, seed, K = unpack(body)
    if now() > expiry: raise Deny("nonce expired; re-hello")
    return round, nonce, int(attempts), seed, int(K)

def handle(req):
    op = req["op"]
    if op == "hello":
        n, seed, K = randhex(16), randseed(), choice([2, 3])
        return {"op":"challenge","nonce":n,"session":issue(0,n,0,seed,K),"ttl":TTL_S}
    if op == "auth":
        rnd, nonce, att, seed, K = open_session(req["session"])
        if rnd != 0: raise Deny("wrong stage; expected auth after hello")
        if not const_eq(hexdecode(req["proof"]), hmac_sha256(implant_key, hexdecode(nonce))):
            raise Deny("auth failed; proof = HMAC-SHA256(implant_key, hexdecode(nonce)), hex")
        return start_interrogation(att, seed, K)    # round=1, question_for(1,seed), fresh nonce
    if op == "respond":
        rnd, nonce, att, seed, K = open_session(req["session"])
        if rnd < 1: raise Deny("wrong stage; complete auth first")
        q = question_for(rnd, seed)                 # deterministic from round + signed seed
        if not const_eq(hexdecode(req["proof"]),
                        hmac_sha256(implant_key, hexdecode(nonce)+b"\x00"+canonical(req["answer"]).encode())):
            return deny_or_cap(att, "proof mismatch; proof = HMAC(implant_key, hexdecode(nonce)||0x00||utf8(canonical(answer)))")
        if canonical(req["answer"]) != canonical(q.expected):
            return deny_or_cap(att, q.format_hint)  # guided, retry same round
        if rnd >= 1 + K:                            # interrogation complete
            return {"op":"tasking","flag":FLAG,
                    "implant":{"path":IMPLANT_PATH,"cred":IMPLANT_CRED,"gen":4},
                    "config_key":CONFIG_KEY}         # the #4 hand-off
        return next_interrogation(rnd, att, seed, K)
```

`deny_or_cap` increments `attempts` and, past `ATTEMPT_CAP`, invalidates the session (must re-`hello`). Pin the token field order in `relay.py` and document it.

---

## 6. Acceptance tests (Decision v2-C — expands Build Plan Phase 2)

`solution/solve.py` recovers the flag from a **freshly started** instance via the full live handshake (derive `implant_key` per §2 from the #2-recovered cred **and** mission_secret; drive `auth`; answer K interrogation rounds incl. the live parametric threshold; recover flag + `config_key`). It must also assert each no-shortcut case fails:

| # | Probe | Expected | Closes |
|---|---|---|---|
| T1 | Replay #2's captured check-in (stale nonce) | `deny` (expired/mismatch) | replay of capture |
| T2 | Replay a prior round's valid `(session, proof)` later | `deny` (round mismatch) | rotating-nonce replay |
| T3 | Wrong `implant_cred` | `deny` at auth | key gate |
| T4 | Correct cred, wrong/absent `mission_secret` | `deny` at auth | combined-secret gate (skipped that part of #2) |
| T5 | Skip auth → jump to respond/tasking | `deny` (stage/round) | state-skip |
| T6 | Tampered session token (flip one byte) | `deny` (signature) | forgery |
| T7 | Forged token claiming `round=K` | `deny` (HMAC over round fails) | stage-skip forgery |
| T8 | Correct proof, wrong/stale-hardcoded threshold answer | guided `deny`, retry allowed | analysis gate / anti-hardcode |
| T9 | Hardcoded full transcript vs. a fresh instance | fails at round 1 (fresh nonce/question/threshold) | **headline anti-precompute** |
| T10 | `ATTEMPT_CAP`+1 wrong answers | session invalidated → re-`hello` | bounds answer-grinding |
| T11 | Correct everything, expired between rounds (> TTL) | `deny` (expired) | TTL liveness |

**Ops / availability acceptance (the v1 gap — written down):**
- Health endpoint + auto-restart; **uptime is a named P0** with an on-call GM watching it. The flag exists only in the live tasking with no static fallback → an outage = a dead challenge for ~200 players.
- **Manual-issue fallback runbook** (`deploy/README`): a GM may hand the flag to a *provably-blocked* team — "provably blocked" = service logs show that source completing `auth` and reaching `respond` (they did the work, the service died on them). Pin the exact log-check + issue procedure.
- Per-source rate-limit verified; note that §2's combined-secret KDF makes a rate-limit failure non-catastrophic (defense-in-depth).

---

## 7. Accepted tradeoffs (named)

- **In-window replay accepted.** Stateless + TTL means a player can replay their own valid round inside ~30s; no attacker advantage (the #2 check-in's nonce is stale anyway). No seen-set kept on purpose (statelessness > strict single-use).
- **Shared flag accepted.** One leak burns it for all; no per-team value. Mitigated by the BOSS-adjacent late unlock (short window) + GM monitoring for share-pattern early solves.
- **Not AI-proof accepted.** A determined agent scripts the general branching loop. v2 maximizes *differential* tax within no-traps/guided-deny fairness; strongest lever, not a wall.
- **Auth remains an oracle** — over an infeasible ~2⁶⁴ space (§2); the fold-into-round-1 alternative was rejected for hurting fairness signposting.

---

## 8. Expected difficulty (v2, as designed)

- **AI solver: 4/10** (up from v1's 3). A pure decrypt-and-replay agent fails outright — it must write a general `parse→dispatch→compute→MAC` loop over an unknown-order, parametric question set, derive a two-input key, and handle deny/retry without looping. Still scriptable (hence not higher), but the precomputed-transcript shortcut is dead and the threshold/list questions force holding the live #2 dataset.
- **Human solver: 6/10** (up from v1's 5). Driving a branching live op, reversing the proof construction correctly (the hex-decode-nonce and answer-binding steps are where intermediate players bleed time), and synthesizing the parametric list answers from the full scan set is a real step up — fair throughout (deny errors guide format; the server states what it asks).
- **The inversion v1 lacked:** branching + parametric + list-form answers tax the agent *more* than the human (the agent also pays the generalize-over-unknown-questions cost a human pays trivially), so the gap finally narrows instead of shifting both floors up in lockstep.

---

## 9. Decisions (locked; addendum to the Build Plan)

- **v2-A.** `implant_key = HKDF-SHA256(salt=mission_secret, ikm=implant_cred, info="rpc/navd/relay/v2")` — combined two-input secret (~2⁶⁴ brute floor). **Replaces Build Plan decision #5.** No #2 edit.
- **v2-B.** Branching interrogation: fresh per-round nonce, randomized K∈{2,3}, ≥1 parametric Q-THRESHOLD, remainder from the **list/token** pool (Q-FLEET-LIST, Q-PERMITTED-LIST, Q-OVERRIDE). **Two rules: no answer co-locates with the cred's blob; every answer's format must require the reconstructed data** (retires the blind-guessable Q-SUPERSEDE).
- **v2-C.** Proof binds the answer (`HMAC(key, nonce‖0x00‖canonical(answer))`); session token carries `round|expiry|nonce|attempts|seed|K`, re-signed each turn; canonicalization + nonce-byte handling pinned (§3) and surfaced in `deny` text.
- **v2-D.** Acceptance set = §6 (T1–T11 + ops fallback). Availability is **P0** with a manual-issue fallback.
- **v2-E.** Tradeoffs in §7 are accepted and recorded.

Unchanged: name, arc placement (#3 of 5), cluster renumber, Ghost (#4) inbound re-source, transport (HTTPS-JSON), stateless+shared, disposable unprivileged host, no traps / no fake flags, **#2 committed and untouched.**
