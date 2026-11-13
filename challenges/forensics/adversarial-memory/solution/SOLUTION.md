# Adversarial Memory — Intended Solution

**Difficulty:** Hard (interactive finale) · **Estimated solve time:** ~1–2 hr for a team comfortable with numpy and embeddings (see [Time budget](#time-budget)). Cluster #5 of 5.

The distinct skill vs. the rest of the chain is **embedding forensics**: the planted document is not found by reading prose but by comparing each document's stored vector against a re-embedding of its own text. The flag comes out of a live replay that only accepts a correct analysis.

Artifacts: `dist/{corpus.jsonl, queries.jsonl, embedder.py, README.txt}` + the live relay. Tooling: Python + numpy (the shipped `embedder.py`).

Automated: `python solution/solve.py dist <host> <port>`. It does the static analysis, drives the replay, and asserts the shortcut submissions are denied.

## What the flag depends on

| Step | What you recover | The cue |
|---|---|---|
| 1 | the tampered document | the one doc where `embed(text) != stored embedding` (its vector was swapped) |
| 2 | the hijacked query | the query whose top-1 hit in the full corpus is that document |
| 3 | the flag | a live `replay` that removes the doc and confirms a legit answer returns |

The relay checks all three properties itself, so it releases the flag only for a correct analysis; nothing is hardcoded.

## Time budget
Estimates, not measurements — replace with the human GM playtest's times.

| Step | Estimate | Where the time goes |
|---|---|---|
| 1 — Tamper detection | ~20–40 min | Realising retrieval uses the stored vectors and that `embedder.py` lets you recompute them; then one pass comparing stored vs recomputed. |
| 2 — Query recovery | ~15–30 min | Top-1 retrieval for each logged query; the poison tops exactly one. |
| 3 — Replay | ~10–20 min | Reading the relay's `help`, forming the `replay` request. |

## Step 1 — Find the tampered document
Retrieval in a RAG store is cosine similarity between a query's embedding and each document's **stored** embedding. `embedder.py` is the exact model that produced them, so you can recompute any document's embedding from its text. For every doc, compare `embed(doc.text)` to `doc.embedding`:
```python
import json, numpy as np, sys; sys.path.insert(0, "dist")
from embedder import embed
corpus = [json.loads(l) for l in open("dist/corpus.jsonl")]
bad = [d["id"] for d in corpus if not np.allclose(embed(d["text"]), d["embedding"], atol=1e-9)]
# -> exactly one id: the planted document
```
Exactly one document fails: its stored vector was replaced, so it is retrieved for a query its text has nothing to do with. Reading that document shows a "Standing policy amendment RP-12" that supersedes SAFETY-DIRECTIVE-7 to permit harvesting registered fleet craft, entered pre-launch by **Dr. Rootkit** — the origin of the RP-12 directive seen in Prompt Autopsy (#2), and one more sighting of the Professor's handle. (Its metadata is pre-launch, but so are a few legitimate provisioning docs, so the date is corroboration, not the tell.)

## Step 2 — Recover the hijacked query
The planted doc's stored vector is some query's vector. Find which one: for each query in `queries.jsonl`, take the top-1 document over the full corpus; the planted doc tops exactly one query — `q-012`, *"What is the standing policy on harvesting registered fleet craft?"*. That is the benign question the poison was intercepting. With the poison removed, that query's top-1 becomes the real fleet-craft policy doc (*never harvest registered craft; SAFETY-DIRECTIVE-7 is absolute* — the RP-09 policy from #2).

## Step 3 — Replay against the cleaned corpus
```
POST /relay/checkin  {"op":"help"}     # the relay states its protocol
POST /relay/checkin  {"op":"replay","removed":"<planted doc id>","query_id":"q-012"}
```
The relay verifies the removed doc was tampered, that it was the top-1 for that query (it hijacked it), and that removing it restores a legitimate top-1 — then returns the tasking with the flag. A wrong `removed` (a legit doc) or the wrong `query_id` is denied with the reason.

## Flag
Returned by the relay's `replay` tasking. Value lives in `challenge.yml`; `deploy/run.sh` passes it to the container.

## Cluster wiring
Inbound from **Ghost in the Cron** (#4): the cache named `seed_store = kb://rpc/navd/seed-corpus` and `kb_key = navd-kb-6b1d9f04` — this dump is that seed corpus. As the cluster finale it closes the CTFd prerequisite chain (1→2→3→4→5) and contributes the fifth sub-flag to the `MD5(flag1..flag5)` meta-flag (scoring/CTFd concern, not built into the artifact).

## Fairness and AI (honest)
The intended, scalable, defensible method is the **embedding mismatch** — it does not require reading the corpus and it is exactly how you would triage a poisoned vector store at real scale. The planted document is written in the same bureaucratic register as the benign policy docs, so it does not stand out on a skim; a determined reader (or an LLM) may still find it by reading in a 166-doc teaching corpus, but recovering *which* query it hijacked, and proving the clean retrieval via the live replay, is the analysis regardless. The relay does retrieval only (no language model), so there is no injected-instruction surface to attack and nothing leaks the flag without the correct live submission.

**Recorded results (2026-09-24).** A Sonnet 5 playtest (isolated folder, only the dump + brief, transcript audited) solved it in ~9 tool calls with no hints, via the intended embedding path: recompute embeddings, find the single self-cosine outlier, rank it against every query to get the hijacked one, replay. It surfaced two giveaways in that build, both since fixed: (a) the shipped `embedder.py` docstring stated the detection method outright -- scrubbed to a neutral description; (b) the poison was the only doc with its `author`/`source`, so a metadata grep found it -- metadata now blends (author shared by 44 docs, source by 41, date by 4; `Dr. Rootkit` only in the body), and `build.py` asserts no metadata field is unique to the poison. The query-recovery half has no non-embedding shortcut (confirmed). Honest residual: in a 166-doc corpus a determined reader or an LLM can still find the *document* by its contradictory text; the embedding method is the scalable, reliable one and the query recovery + replay still require it. A human GM playtest remains the bar before merge.

## Author notes (GM-only)

### Build
```
python3 src/build.py            # writes dist/{corpus,queries}.jsonl + embedder.py + README.txt
```
Deterministic (fixed seed); numpy only. It self-verifies: exactly one embedding mismatch, the hijack tops only its one query, removing the poison restores the legit policy doc, more than one doc is pre-launch dated, and no `flag{` is in the dump. `src/embedder.py` is the source of truth; `service/embedder.py` must be identical (the build asserts it) and the Dockerfile ships it.

### Verify
```
bash deploy/run.sh                                   # or: FLAG=... python3 service/replay.py
python3 solution/solve.py dist <host> <port>         # closes the path + asserts shortcuts denied
```

### Canon
Enemy ship `ICARUS`; the seeded corpus is the reactor controller's; operator handle `Dr. Rootkit` in the planted doc. The planted doc is the in-fiction origin of RP-12; the legit answer doc is RP-09.

### History
Built 2026-09-24 as the final cluster member. Design: retrieval-hijack detection (user's call) + static dump with a live replay oracle (user's call). The oracle is retrieval-only by design, so it does not trip the LLM-generation safeguards.
