# Gjallarhorn — solution (GM only)

Run: `docker compose up -d` then `python solution/solve.py --url http://localhost:8080`
(or `--data src/ui/public` offline). The script uses only `graph.json` / `chat.json`, asserts a
unique answer, and prints the flag from the validator.

## Steps
1. **Token.** Heimdall's cut-off lines keep what he really sent in `raw`; the frame `trace`
   holds a fragment `i/6:<chars>`. Join in order -> signed launch token.
2. **Infected set.**
   - Forged cancels: system frames where `sig != expectedSig` -> 16-node superset.
   - HATI relay messages with a node as `origin` -> a partial set (+ HATI).
   - Rule (stated by Heimdall: spreads by contact, plus strays): connected cluster of 6 around
     HATI + 2 isolated strays, 8 total. Exactly one set fits.
   - `H13MD411` frames have non-Heimdall signatures; ignore their "all is well".
3. **Activation code.** Heimdall: ledger is in his core. CORE glyph -> ledger -> rune codex.
   Bind-rune = first 3 letters. Each region is a sea of ~50 nodes; the 15 on HATI's relay mesh (the `relay` links, which the relay trace lights) form one rune. Order = how far HATI's relay
   reaches (relay trace, or BFS over the `relay` links of `graph.json`): regions
   outward from HATI; the 4 nearest then the 4 farthest give letters 4-11. Case/hyphens ignored.
4. **Fire.** Enter code + token, select the 8 nodes, submit.

## Notes
- Regenerate with `src/gen_nodes.py` (asserts everything, deterministic). Re-run `solve.py` after.
- Only `src/ui/public/*` and the UI bundle are public; `src/server/secret.json` stays in the image.
- Rate limits: check 60/min/IP; purge burst 10 then 60/10 min (HTTP 429 with `retryAfter` seconds, shown in the console). Set `TRUST_PROXY=1`
  behind a reverse proxy.
