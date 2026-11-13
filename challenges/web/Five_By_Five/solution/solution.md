# Five By Five — Solution

## Real-world grounding

**CWE-602, Client-Side Enforcement of Server-Side Security.** The page enforces "one guess
only" entirely in its own JavaScript: after the first response, it disables the input and
submit button and shows "You've used your one attempt." That is a UI-level restriction, not
a security boundary. The session mechanism makes this explicit: on load, the page calls
`GET /api/session` once to get a `session_id`, then uses it for exactly one visible guess.
The server was never told "this id only gets one guess" — a `session_id`, once obtained, is
just a string that `POST /api/guess` will keep honoring forever, with no guess-count limit,
no cookie, and no requirement that the page which first fetched it ever be reloaded. A
client that calls `/api/session` itself and reuses that id directly gets exactly the same
full per-letter feedback as the page did, as many times as it wants.

## The encoding

`src/wordle/app.py` picks a random 5-letter word from `WORD_BANK` for each new session and
stores it against that session's `session_id` in memory. `/api/guess` scores any 5-letter
guess for a given `session_id` with the same duplicate-letter-aware Wordle/Mastermind logic
used in Daily Uplink's oracle (`hit` = right letter, right position; `present` = right
letter, wrong position; `absent` = not in the secret anywhere), and returns `flag` in the
payload the moment a guess matches that session's word exactly. Nothing about this scoring
or response changes between the first call and the fiftieth, for as long as that
`session_id` keeps being reused.

## Solve path

1. Load the page once — notice it calls `GET /api/session` on load (visible in the browser's
   network tab) to get a `session_id`, then POSTs that id alongside a guess to `/api/guess`.
2. Recognize the one-guess lock only ever runs in the page's own `<script>` — the
   `session_id` itself carries no "already used" state server-side.
3. Call `/api/session` directly to get your own id (or simply reuse the one the page already
   fetched), then script repeated `/api/guess` calls with that same id: use the real
   per-letter feedback from each response to narrow the secret, the same way a human plays
   Wordle, until a guess comes back `"solved": true`.
4. That response includes the flag directly.

The real friction is step 2 — noticing the restriction is cosmetic and tied to nothing the
server actually enforces — not the scoring logic itself, which is given away in full by the
page's own documented tile colors.

## Solve Script

See `solution/solve.py` — calls `/api/session` once (exactly like the page's own first load
does), then hits `/api/guess` directly and repeatedly with that same id (never touches the
browser page), using an adaptive elimination strategy to converge on the secret in a handful
of requests:

```bash
cd solution
pip install -r requirements.txt
python solve.py http://localhost:8080
```

Expected output ends with the exact flag from `challenge.yml`.

## Verification

- Brought up the live service (`docker compose up -d --build`), loaded the page, submitted
  one guess through the browser, and confirmed the input/button disable afterward exactly
  as designed.
- Separately called `GET /api/session` for a fresh id, then `POST /api/guess` with it
  multiple times — confirmed it kept returning full feedback every time, proving the lock is
  client-side only and the session id itself carries no per-guess limit.
- Ran `solution/solve.py` against the live service end-to-end and recovered the exact flag:
  `flag{client_side_lock_isnt_a_lock}`.
- Confirmed two different sessions (two separate `/api/session` calls) get independently
  randomized words from `WORD_BANK`, and that solving one session's word has no effect on
  any other session.
- Leak check (`grep -RnoE 'flag\{[^}]*\}' dist/ README.md src/`) clean — the real flag lives
  only in `challenge.yml`, `docker-compose.yml`, and here.
