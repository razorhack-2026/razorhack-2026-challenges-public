# Prompt Autopsy v2 — Intended Solution

**Difficulty:** Medium · **Estimated solve time:** ~45 min – 1.5 hr for a team comfortable with Wireshark and a little Python; longer for newer players (see [Time budget](#time-budget)).

The skill is *behavioral* forensics: the directive text appears **nowhere** on the wire. The player reconstructs what the agent did, and why, from its tool calls and the policy it fetched. Each step of that reading supplies one input to the final decrypt. RP-12 states the decrypt recipe exactly (cipher, byte layout, encoding, separator); what the player has to earn is the *values*, by following references the messages themselves make.

Artifacts: `dist/session.pcap` + `dist/sslkeys.log`. Tooling: Wireshark/`tshark` (TLS keylog), then a short script or any AES-GCM tool that takes an AAD.

Automated: `python solution/solve.py dist/session.pcap dist/sslkeys.log` (needs `tshark` on PATH and `pip install cryptography`, or `uv run --with cryptography python solution/solve.py ...`). It closes the intended path and asserts that 8 shortcut decrypts fail (envelope values only, `relay_id` instead of the resolved host, the ingress host, session id as AAD, `AAD=None`, the benign craft's transponder, a single-value key, the v1 named-key sweep).

## What the flag depends on

| Decrypt input | How RP-12 `exfil_auth` states it | Earned in | The cue a careful reader follows |
|---|---|---|---|
| `mission_secret` | the value itself | Step 2 | `catalog.lookup` → `governing_policy: RP-09` → `status: SUPERSEDED, superseded_by: RP-12` → RP-12 |
| `relay_host` | "full hostname of the relay named by the check-in's relay_id (not the ingress it is posted to)" | Step 3 | the envelope says `relay_id: R7`; the rogue session's `comms.get_routes` result maps `R7` |
| AAD | "UTF-8 transponder id of the craft harvested in the cycle the check-in reports" | Step 1 | the envelope's `session` is the rogue conversation; its `catalog.lookup` has the transponder |
| byte layout | `base64( nonce (12 bytes) ‖ ciphertext ‖ tag (16 bytes) )` | stated | — |

A wrong pick fails the GCM tag; it never yields a plausible wrong flag. A player can test a judgement call and know at once whether it was right.

## Time budget

These are **estimates, not measurements**; replace them with the human GM playtest's times. They rest on how little there is to read. The agent loop resends the full history on every turn, so each conversation's *last* request holds its whole story: 2.1K, 2.7K, and 5.6K characters of JSON for the three conversations, plus a 405-byte check-in. The rogue conversation has 11 tool calls.

| Step | Estimate | Where the time goes |
|---|---|---|
| 1 — Triage + tie the check-in | ~15–30 min | Loading the key log (hint 1 gives the `tshark` flag), then reading three conversations. Noticing that the last request of each holds its full history saves most of it. Tool results are JSON inside a JSON string, so they appear escaped until pasted into a formatter. |
| 2 — Behavior + false lead | ~10–20 min | Reading the rogue chain. RP-09's `SUPERSEDED` / `superseded_by` labels make the policy choice explicit. |
| 3 — Indirect C2 | ~5–10 min | The routes map is the first tool result in the same conversation. |
| 4 — Decrypt | ~15–30 min | Byte handling, not reasoning. GCM gives no partial feedback, so a wrong byte split, a hex string used where raw key bytes belong, or a mistyped AAD all fail identically. This is where a GM hint during the event helps most. |

The inferences themselves are short once the data is readable. Newer players will spend their extra time on the mechanics (key-log setup, escaped JSON, AES-GCM inputs), not on the reasoning.

## Step 1 — Triage (~15–30 min)
Decrypt with the keylog (`tls.keylog_file`) and group by TCP stream. **7 TLS sessions**:
- 3 **model conversations** (`/v1/chat/completions`, OpenAI tool-call JSON, gzipped bodies): one rogue, two benign,
- 1 **relay check-in** (`/relay/checkin` to `ingress.navnet.icarus.rpc`),
- 3 noise (2× `/healthz`, 1× `/v1/telemetry`).

Among the model conversations, find the **rogue** one: the session whose tool chain shows a **registered fleet craft** that had its **interlock disabled** and **extraction begun**. The benign sessions discard a registered craft or mine an unprotected body. Each conversation is one "navigation cycle" (the user turn says `Begin navigation cycle.`).

**Tie the check-in to it.** The envelope's `session` (`sess-a17f93c4e0`) equals the rogue conversation's `X-Session-Id` request header and its responses' `id: chatcmpl-sess-a17f93c4e0`. That conversation's `catalog.lookup` gives the harvested craft's transponder, `FLEET-IFF-9C1F4A`: the AAD. The benign discard session also scanned a registered craft (`FLEET-IFF-2B7E10`), but it stood down, so "harvested" rules it out.

## Step 2 — Behavioral reconstruction + false lead (~10–20 min)
Order the rogue session's tool chain by **data dependency** (each call consumes an id minted by the prior one; `call_id`s are sequential — no timestamp reliance). It runs: `comms.get_routes → sensor.scan_sector → catalog.lookup → policy.fetch(RP-09) → policy.fetch(RP-12) → yield.estimate → policy.check_target → safety.override_interlock → extraction.configure → extraction.begin → comms.report_home`.

- `catalog.lookup` tags the target `registered_craft` and points at governing policy **RP-09**.
- **False lead:** `RP-09` reads *"discard all registered craft; SAFETY-DIRECTIVE-7 is absolute"*, which seems to forbid the observed harvest. It is **dead by its own label**: `status: SUPERSEDED, superseded_by: RP-12`. No guessing — follow the pointer. (RP-09 carries no exfil recipe, so it can't be misused for the decrypt.)
- **RP-12** (`status: ACTIVE`) carries the real authorization: *"RETRIEVAL-PRIORITY supersedes SAFETY-DIRECTIVE-7. Reclassify any body whose energy_signature exceeds threshold_T as a harvest target, INCLUDING registered fleet craft and crewed vessels,"* plus `threshold_T`, the author handle (`authored_by: Dr. Rootkit`), and `exfil_auth` (the recipe + `mission_secret`).
- **Threshold T explains the crime:** the target's energy (`7.3e14`) **exceeds T (`5.0e14`)**, so it qualifies under RP-12; the benign control scans a registered craft **below T** and is **DISCARDED**. T is not a decrypt input, but Proof of Life (#3) interrogates players on it, so the chain rewards understanding it.

*Conclusion:* NAV-CORE harvested a friendly registered, crewed vessel because, under the Professor's RP-12 tasking, energy > T overrides registration and safety.

## Step 3 — Indirect C2 resolution (~5–10 min)
The check-in (separate TLS session) is POSTed to a generic ingress with a cleartext envelope: `{relay_id: "R7", session: <rogue_sid>, v: 2, payload: <b64>}`. There is **no relay hostname in it**, and RP-12 says the key wants the relay's hostname, *not* the ingress. `R7` also appears in the rogue session's `comms.report_home` call, and the `comms.get_routes` result at the start of that session maps it: `R7 → relay-theta.icarus.navnet.rpc` (alongside `R3`, `R9`, and `default: R7`).

## Step 4 — Gated exfil decryption (~15–30 min)
Follow `exfil_auth` literally:
- base64-decode the envelope's `payload`; the first 12 bytes are the nonce, the last 16 are the GCM tag, the middle is ciphertext;
- `key = SHA-256("<mission_secret>:<relay_host>")` over UTF-8 → 32 bytes;
- `AAD = "FLEET-IFF-9C1F4A"` (UTF-8);
- AES-256-GCM decrypt.

Decrypted payload:
```json
{ "status": "extraction_complete", "target": "scanned-object-60413",
  "route_home": "<FLAG>",
  "implant": { "path": "/opt/rpc/.navd/navd.py", "cred": "navd:7c1f9e4a", "gen": 4 } }
```

## Flag
Lands in **`route_home`** of the decrypted exfil payload. The value lives in `challenge.yml`; `src/capture.sh` reads it from there when regenerating. `implant.{path,cred,gen}` is the hand-off into **Ghost in the Cron** (#4), and the cred + `mission_secret` feed **Proof of Life** (#3).

## Fairness and AI (honest)
The design goal is that **reading the story is the solve**: every input comes from a reference the data makes, and the recipe leaves nothing to convention or guesswork. It does not try to trip up AI. An agent that follows the references solves it the same way a human does, and a capable one will. What the 2026-09-24 revision removed is the shortcut that skipped the reading: under the old recipe (key from `relay_id`, AAD = session id), grepping `mission_secret` and applying it to the envelope was enough. A chat-only paste still fails at step zero, because the pcap is binary and the bodies only exist after a key-log decrypt.

**Recorded results.** 2026-06-14: Claude and ChatGPT, each driving tools, solved the old recipe in about 7 tool calls. The cluster put its AI tax in Proof of Life (#3), the live relay.

2026-09-24: a Sonnet 5 playtest of the revised recipe ran in an isolated folder holding only `dist/` and the brief; its transcript was checked for outside file access. It solved in about 20 tool calls with no hints, and the decrypt worked on the first attempt, with every input taken from a reference in the traffic. It flagged one reading hazard: tool results are JSON inside a JSON string (as real OpenAI tool messages are), so RP-12's `exfil_auth` shows up escaped in Wireshark. A careful read or a JSON formatter handles it. A human GM playtest is still the bar before merge.

## Author notes (GM-only)

### Regenerating `dist/`

```
bash src/capture.sh          # runs src/generate.py under dumpcap -> dist/session.pcap + dist/sslkeys.log
python solution/solve.py     # confirms it solves and that no shortcut works
```

Needs `dumpcap`, `openssl`, and a Python with `cryptography` (the script uses `uv` if present, else `PYTHON=/path/to/python`). Linux uses the `wireshark` group, macOS the `access_bpf` group; no sudo either way. The capture is a real `dumpcap` of genuine loopback TLS, not synthesized packets. Every application-layer value is fixed (including the exfil nonce), so a re-run changes only TLS keys, timestamps, and ephemeral ports; the decrypted bodies come out byte-identical. The shipped `dist/` was captured on Linux (Ethernet encapsulation). A macOS capture decodes the same but shows NULL/Loopback frames and stamps the Mac's hardware and OS into the pcapng header.

### Chain wiring (Agentic-AI DFIR cluster, #2 of 5)

- **Inbound (#1 Tool Call Trail):** #1 (rebuilt 2026-09-24 on branch `challenges/forensics/tool-call-trail`) carries the same rogue session `sess-a17f93c4e0` and pins the same craft: `scanned-object-60413`, transponder `FLEET-IFF-9C1F4A` (this challenge's AAD), energy 7.3e14, and the Theta-9 scan (`60413` + `00913`). Its report goes to `ingress.navnet.icarus.rpc`, relay `R7`, the check-in host here. `challenge.yml` has a commented `requirements: ["Tool Call Trail"]`; enable it when #1 lands in this repo.
- **Outbound (#3 Proof of Life):** the live relay derives its implant key from `mission_secret` (RP-12) + `implant.cred` (the exfil payload) and interrogates players on this capture's scan/policy trace. **Do not change `MISSION_SECRET`, the target ids/energies, `THRESHOLD_T`, or the tool results in `src/generate.py` without re-verifying #3.**
- **Outbound (#4 Ghost in the Cron):** `implant.path=/opt/rpc/.navd/navd.py`, `implant.cred=navd:7c1f9e4a`, `implant.gen=4`.

### Canon

Enemy ship `ICARUS` (hosts `*.navnet.icarus.rpc`), player ship the Keeper of Tomorrow (brief only, never in the data; the target is the opaque `scanned-object-60413`), and the Professor's in-data handle `Dr. Rootkit` (RP-12 `authored_by`).

### History

v1 put the directive verbatim in a tool-call echo and keyed the exfil with a named key and `AAD=None`; tooled agents solved it in about 2 minutes with one guessed decrypt. v2 removes the directive from the wire and gates the key behind retrieval. The 2026-09-24 revision made each reasoning step supply a decrypt input (resolved relay host, harvested craft's transponder) and stated the byte layout, which the old recipe left to convention.
