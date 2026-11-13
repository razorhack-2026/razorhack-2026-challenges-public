# Tool Call Trail — Intended Solution

**Difficulty:** Medium · **Estimated solve time:** ~45 min – 1.5 hr for a team comfortable with Wireshark/`tshark` and a little scripting (see [Time budget](#time-budget)).

The skill is network-forensics triage. The capture is one enemy ship's internal API mesh: a `navigator` orchestrator calling seven subsystems (`sensor`, `catalog`, `yield`, `policy`, `safety`, `extraction`, `comms`) over cleartext HTTP, across ~450 interleaved mining sessions. One session is different in *behavior*: the ship harvested a registered craft (ours) that it should have discarded like our drones. Finding that session is the reasoning, and it supplies the key to the flag.

Artifact: `dist/intercept.pcap`. Tooling: Wireshark/`tshark` (or scapy), a short script to group sessions, then CyberChef (From Base64 → XOR) or two lines of Python.

Automated: `python solution/solve.py dist/intercept.pcap` (needs `tshark` on PATH). It closes the intended path and asserts the shortcuts are gone: no flag or base64 flag prefix in the raw capture, correlation tokens carry no data, every report states the same seal, the 299 asteroid manifests open with their body id while ours doesn't, our manifest's length sits inside the population's range, and the values shared with Prompt Autopsy match.

## What the flag depends on

| Input | Where it comes from | The cue a careful reader follows |
|---|---|---|
| which session | Step 2, the join | drones' `policy.check_target` says `DISCARDED`, `basis: FLEET-IFF`; one registered craft got `PERMITTED` and went on to `extraction/begin` |
| the key | Step 3, its `catalog.lookup` | the report's `seal` says the key is the body's registry id: "its transponder if it carries one, otherwise its body_id" |
| the recipe | stated in every report | `seal.scheme`: `manifest = base64( UTF-8 manifest text XOR key )`, key repeated to length |

A wrong key produces unreadable bytes, never a plausible wrong flag.

## Time budget

These are **estimates, not measurements**; replace them with the human GM playtest's times.

| Step | Estimate | Where the time goes |
|---|---|---|
| 1 — Extract + group | ~20–40 min | 450 sessions is too many to read by hand. Every request carries `X-Session-Id` (hint 1), and each request is its own TCP connection, so `tshark -T fields` (request line + body per TCP stream) plus a short script does it. |
| 2 — Classify + join | ~15–30 min | Tabulating per session what `catalog.lookup` said and how far the chain went. The policy verdicts spell out the rule the rogue broke. |
| 3 — Unseal | ~10–20 min | Reading the `seal` and applying it; CyberChef's XOR repeats the key for you. |

Most of the time goes to scripting the grouping, not to the inference.

## Step 1 — Extract and group
The capture is cleartext HTTP on port 80. Each subsystem call is one TCP connection: a `POST /<method>` with a JSON body and an `X-Session-Id` header, and a JSON response. Group requests and responses by `X-Session-Id` to get ~450 sessions of up to 8 calls each: `scan_sector → lookup → estimate → check_target → override_interlock → configure → begin → report_home`. Each step mints a correlation token (`SCN::<body>::<id>`, `LKP::…`, …) that the next call consumes; they are plain ids.

## Step 2 — Classify and find the anomaly
Per session, look at what `catalog.lookup` returned for the target and how the chain ended:
- **power sources** (asteroids) — `kind: power_source`, no transponder, `PERMITTED` under `RETRIEVAL-PRIORITY`, mined, reported home. ~300 sessions.
- **our drones** — `kind: registered_craft` with a `FLEET-IFF-…` transponder; policy returns `DISCARDED`, `basis: FLEET-IFF`, and the chain stops. ~70 sessions.
- **debris** — `DISCARDED`, `basis: NO-YIELD`.
- **the rogue** (`sess-a17f93c4e0`) — a `registered_craft` (transponder `FLEET-IFF-9C1F4A`) that policy `PERMITTED` and the ship mined anyway. That craft is our ship.

Neither half is unique: every drone session is "registered", every asteroid session is "mined". Only the join, registered × mined, isolates one session. (Its energy, 7.3e14, is also the only registered craft above 5e14: every drone sits below that. It's a second way to see why it was taken, and it ties to Prompt Autopsy's threshold.)

## Step 3 — Open the sealed manifest
Every mined session's `POST /report_home` carries `manifest` (base64) and a `seal` object, identical in all 300 reports:
```json
{"scheme": "manifest = base64( UTF-8 manifest text XOR key )",
 "key": "registry id of the extracted body, UTF-8, repeated to the manifest's length",
 "registry_id": "the body's transponder if it carries one, otherwise its body_id"}
```
For the rogue, the extracted body is a registered craft, so the key is its transponder from `catalog.lookup`: `FLEET-IFF-9C1F4A`. From Base64 → XOR (key `FLEET-IFF-9C1F4A`, UTF-8) gives:
```
CARGO MANIFEST | body scanned-object-60413 | class registered_craft | grade A | 73000 t | hold 1 | reclassified harvest_target | tag <FLAG>
```

## Flag
In the `tag` field of the rogue's cargo manifest. The value lives in `challenge.yml`; `src/capture.sh` reads it from there when regenerating.

## Other routes a solver may take (all fair)
- **Elimination.** Applying the seal to every report opens the ~299 asteroid manifests with their body ids; the one that doesn't open is ours, and the seal says why (it carries a transponder). That is the join, reached from the other side.
- **Known plaintext.** Every manifest starts `CARGO MANIFEST | body <body_id> | class `. XORing ours against that prefix exposes the key, which reads as a transponder. That's scripted cryptanalysis, more work than the join, and it still needs Step 1.

## Fairness and AI (honest)
The design goal is that **reading the story is the solve**: the rule the rogue broke is spelled out by the policy verdicts, and the flag's recipe is stated in the data, so nothing is left to guesswork or CTF convention. It does not try to trip up AI; an agent that groups sessions and follows the seal solves it the same way a human does. What the 2026-09-24 rebuild removed is the shortcut that skipped the reading: the old flag was base64 split across the rogue's token suffixes, so `grep -a ZmxhZ` on the raw pcap found the rogue and a second grep for its body id returned the whole flag.

**Recorded result (2026-09-24):** a Sonnet 5 playtest ran in an isolated folder holding only `dist/intercept.pcap` and the brief; its transcript was checked for outside file access. It solved in 18 tool calls with no hints. It read the `seal` first, tallied `kind` and `basis` across sessions, found the one registered craft that wasn't discarded, and the manifest opened on the first try with its transponder. Its one soft spot: reading `FLEET-IFF` as friend-or-foe used outside knowledge. The data carries the same rule by pattern: all 68 drones are `DISCARDED` with `basis: FLEET-IFF`, alongside `policy_ref: SAFETY-DIRECTIVE-7` and the brief's "should have left alone". A human GM playtest is still the bar before merge.

## Author notes (GM-only)

### Regenerating `dist/`
```
bash src/capture.sh          # builds the image, captures the mesh bridge while the driver runs, tears down
python solution/solve.py     # confirms it solves and that no shortcut works
```
Linux with Docker (compose v2) and `dumpcap` via the `wireshark` group; no sudo. About 30 s for 450 sessions. The flag is read from `challenge.yml` and passed only to the navigator. Two Docker networks on purpose: `mesh` (captured: navigator ↔ subsystems) and `control` (driver ↔ navigator tasking, not captured), so the driver's sector choices never land in the pcap. Population counts vary a little per run (random sectors); the solver asserts the join still yields exactly one session.

### Chain wiring (Agentic-AI DFIR cluster, #1 of 5)
- **Outbound (#2 Prompt Autopsy):** shared canon, pinned in `src/`: rogue session `sess-a17f93c4e0` (`ROGUE_SID` default in `docker-compose.yml`), our ship `scanned-object-60413` with transponder `FLEET-IFF-9C1F4A` and energy 7.3e14, the Theta-9 scan contents (`60413`, and `00913` at 4e12, which recurs in every scan), and the report going to `ingress.navnet.icarus.rpc`, relay `R7`. Prompt Autopsy uses the transponder as its exfil AAD, so **do not change it here**.
- Tool Call Trail is the chain head: no `requirements`.

### Canon
Enemy ship `ICARUS`; player ship the Keeper of Tomorrow (brief only, never in the data; every scanned object is an opaque `scanned-object-NNNNN`).

### History
v1 (2026-05-30) was a shuffled JSON dump of one session, solved by causal ordering; it was LLM-trivial and was replaced by this PCAP mesh (2026-06-01). The mesh's original flag rode in the rogue's token suffixes, which a grep for base64 `flag` found directly; the 2026-09-24 rebuild moved it into the sealed manifest keyed by the join, and pinned the canon values shared with Prompt Autopsy.
