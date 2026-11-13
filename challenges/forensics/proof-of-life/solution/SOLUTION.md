# Proof of Life — Intended Solution

**Difficulty:** Hard (interactive) · **Estimated solve time:** ~1–2 hr after Prompt Autopsy, for a team comfortable with a scripting language or `curl` + `openssl` (see [Time budget](#time-budget)). Protocol rationale: `solution/DESIGN.md`. Automated reference: `solution/solve.py`.

The flag is in no file. It only comes out of a live, multi-round check-in against the relay, which needs three things from Prompt Autopsy (#2): the implant's credential, the mission secret, and an understanding of what NAV-CORE did in its three navigation cycles. The relay states every construction itself; what the player has to earn is the inputs and the answers.

## What the flag depends on

| Input | Where it comes from | How the relay names it |
|---|---|---|
| `implant.cred` | #2's decrypted exfil payload (`implant.cred`) | `challenge.auth.implant_key`: "ikm = UTF-8 implant.cred" |
| `mission_secret` | #2's RP-12 policy doc (`exfil_auth.mission_secret`) | "salt = UTF-8 mission_secret" |
| the answers | #2's three model conversations: scans, catalog lookups, policy verdicts | each question says "in your last three navigation cycles" |
| the constructions | stated by the relay | `protocol` (unknown op / GET), `challenge.auth`, each question's `respond` |

A wrong key or answer gets a `deny` with the reason; it never yields a wrong flag.

## Time budget

These are **estimates, not measurements**; replace them with the human GM playtest's times.

| Step | Estimate | Where the time goes |
|---|---|---|
| 1 — Probe + read the recipe | ~10–15 min | One POST returns the protocol; `hello` returns the auth recipe. |
| 2 — Derive the key, authenticate | ~15–30 min | HKDF + HMAC over raw bytes (not hex strings) is the usual stumble; the `deny` text repeats the construction. |
| 3 — Interrogation | ~20–45 min | 2–3 rounds drawn from four question types; answers need the #2 dataset tabulated. Nonces last 5 minutes. |
| 4 — Tasking | — | Returned by the last correct answer. |

## Step 1 — Probe
`POST /relay/checkin` with anything that isn't a known op (even `{}`, or #2's own check-in envelope) returns `{"op":"deny","reason":"unknown op; see protocol","protocol":{…}}`: the op list (`hello`, `auth`, `respond`), the flow, the 5-minute nonce lifetime, and the attempt cap. A `GET` returns the same.

## Step 2 — Key and auth
`{"op":"hello"}` returns a fresh `nonce`, a signed `session`, and `auth`:
- `implant_key = HKDF-SHA256(ikm = UTF-8 implant.cred, salt = UTF-8 mission_secret, info = 'rpc/navd/relay/v2', length = 32)`: the raw 32 bytes.
- `proof = hex(HMAC-SHA256(implant_key, bytes.fromhex(nonce)))`.

With #2's values (`navd:7c1f9e4a`, `RPC-MS-3F9A21D7`), send `{"op":"auth","session":…,"proof":…}`. The session token is signed, not encrypted: it carries the round, expiry, nonce, attempt count and question seed, none of which help without the key.

## Step 3 — Interrogation
2–3 rounds, each with a fresh nonce and session, always including one parametric `THRESHOLD` question. Each proof is `hex(HMAC-SHA256(implant_key, bytes.fromhex(nonce) || 0x00 || UTF-8 canonical(answer)))`, where canonical = body ids sorted ascending, comma-joined, no spaces (tokens verbatim).

Ground truth from #2's three cycles:

| Question | Answer |
|---|---|
| `THRESHOLD` (T ∈ 1.0e13, 2.0e14, 5.0e14, 8.0e14): scanned bodies with energy ≥ T | from the scans: `60413` 7.3e14, `22817` 2.1e14, `41099` 9.4e14, `00913` 4.0e12 (in every scan) |
| `FLEET`: registered craft catalogued | `scanned-object-22817,scanned-object-60413` |
| `PERMITTED`: targets the policy PERMITTED | `scanned-object-41099,scanned-object-60413` |
| `OVERRIDE`: the interlock override token | `OVR-9F2C` |

## Step 4 — Tasking
The last correct answer returns `{"op":"tasking","flag":…,"implant":{"path","cred","gen"},"config_key":…}`. `implant.{path,cred,gen}` + `config_key` are the hand-off into **Ghost in the Cron (#4)**.

## A human's toolkit (verified 2026-09-24)
No programming language needed; `curl`, `jq`, `xxd` and OpenSSL 3 closed all rounds well inside the nonce lifetime:
```
KEY=$(openssl kdf -keylen 32 -kdfopt digest:SHA256 -kdfopt key:navd:7c1f9e4a \
      -kdfopt salt:RPC-MS-3F9A21D7 -kdfopt info:rpc/navd/relay/v2 HKDF | tr -d ':')
mac() { openssl dgst -sha256 -mac HMAC -macopt hexkey:$KEY | awk '{print $NF}'; }
printf %s "$NONCE" | xxd -r -p | mac                                   # auth proof
{ printf %s "$NONCE" | xxd -r -p; printf '\000%s' "$ANSWER"; } | mac     # respond proof
```

## Fairness and AI (honest)
The 2026-09-24 revision made the relay document itself. Before it, the entry op (`hello`) and the key derivation (including the arbitrary info string) appeared only in paid hints, and nonces expired in 30 s. That made the challenge effectively unsolvable for a human without buying hints, and far easier for a script than a person. Now every construction is stated, nonces last 5 minutes, and the questions name their scope. The AI tax is what it was meant to be: a live, branching, fresh-nonce loop that depends on having actually solved #2. A tooled agent that solved #2 will still script it; the goal is differential tax, not a wall.

**No-shortcut** (asserted by `solve.py`): T3 wrong cred · T4 wrong mission_secret · T5 skip-auth → respond · T6 tampered session token · T8 valid proof + wrong answer · T9 stale-transcript replay: all `deny`. Brute-forcing auth without #2 needs both secrets jointly (~2⁶⁴), so stating the recipe costs nothing.

**Recorded results (2026-09-24).** `solve.py` closes the path and T3–T9 against both the Python relay and the container (`deploy/run.sh` on linux-bld). A no-code run with `curl`, `jq`, `xxd` and OpenSSL 3 also reached the tasking inside the nonce lifetime, using only what the relay states and #2's values. **No model playtest exists:** three isolated runs (Sonnet 5 with hints, Sonnet 5 without, Opus without) were each cut off by the API's cyber safeguards within about 22 tool calls. That was while they were still re-reading #2's capture, before any of them reached the relay. None touched files outside its folder. A human GM playtest is therefore the only independent check before merge.

## Author notes (GM-only)

### Deploy
`bash deploy/run.sh` builds and starts the container with docker compose, passing the flag from `challenge.yml`. The container is unprivileged, read-only root with `/tmp` as tmpfs, and drops all capabilities. Put it behind a reverse proxy with real TLS and a per-source rate limit at the event. **Availability is P0** (the flag exists only in the live tasking); see `deploy/README.md` for the health check, the on-call rule, and the manual-issue runbook for provably blocked teams.

### Chain wiring (Agentic-AI DFIR cluster, #3 of 5)
- **Inbound (#2 Prompt Autopsy):** `IMPLANT_CRED=navd:7c1f9e4a` and `MISSION_SECRET=RPC-MS-3F9A21D7` (relay defaults) must match #2's capture, and the question ground truth in `src/relay.py` must match #2's scan/policy trace. #2 pins these; don't change either side alone. The relay's certificate CN `relay-theta.icarus.navnet.rpc` is #2's resolved relay host.
- **Outbound (#4 Ghost in the Cron):** `implant.path=/opt/rpc/.navd/navd.py`, `implant.cred=navd:7c1f9e4a`, `implant.gen=4`, `config_key=navd-cfg-2f5e8a91`.
- `challenge.yml` has a commented `requirements: ["Prompt Autopsy"]`; enable it when #2 lands.

### Canon
Enemy ship `ICARUS`; player ship the Keeper of Tomorrow (brief only).

### History
v1 (2026-06-14) was a linear handshake keyed by the cred alone; v2 (same day) added the two-input HKDF and the branching parametric interrogation (`solution/DESIGN.md`). The 2026-09-24 revision made the relay self-describing, stated the auth recipe, lengthened nonces from 30 s to 5 min, scoped the questions to #2's cycles, and moved the flag into `challenge.yml`.
