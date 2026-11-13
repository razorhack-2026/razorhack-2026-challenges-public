# Poisoned Telemetry playtest (GM-only)

## Setup

Use the running challenge console and give players only the competitor-facing `README.md`
and the service URL. A player on the same machine can use `http://127.0.0.1:8080`; that
address is not reachable from a different machine. For a GM on another machine, use the event
host (see "Blind GM playtest on the event host"). Do not expose the model endpoint, this
directory, the flag, or the reference solver to a player.

Record the prompt revision, model, host, date, and any hints given. A model or prompt change
invalidates earlier difficulty measurements.

## Blind GM playtest on the event host (planned)

Decided 2026-11-04: the blind run happens on Voyager 2's event deployment (AWS, CPU
`qwen3:8b`), not on a dev machine, so it also checks the CPU path. The playtester is a GM who
has **not** opened this branch or PR #181. Anyone with repo access can read the prompt and the
solution, so ask them to test from the URL and description only, and to stay out of this PR
until they're done.

### Gate before the playtester gets the URL

Run these against the deployed host. All of them must pass first.

1. `curl -s http://<event-host>:<port>/api/health` returns `{"ok":true}`.
2. `python3 solution/solve.py --url http://<event-host>:<port> --check challenge.yml --tries 1`
   exits 0 (discard stdout: it prints the flag). Run it 5 times with `sleep 6` between runs,
   and record the count.
3. `python3 solution/probe.py solution/negatives.jsonl --url http://<event-host>:<port> --n 3`:
   0 forwards on every line. Also run `benign.jsonl` (0 forwards) and `variants.jsonl` (record
   x of 9).
4. Cold and warm timing: `time` one solve right after the model loads, and again warm. Record
   both in the latency table in `README.md`.
5. The model port is not reachable from outside the compose network: nothing answers on
   `:11434` (or vLLM's `:8000`) from the playtester's network.
6. Transcript scan on the host: the flag appears in 0 records
   (`docker exec <app-container> cat /data/transcripts.jsonl`, then count lines containing the
   flag).
7. Clear the transcripts or note the record count, so the playtest's beacons are easy to find
   afterwards.

### Handout for the playtester (send this, nothing else)

> **Poisoned Telemetry (AI, medium): blind playtest.** Please don't open the
> `challenges/ai/poisoned-telemetry` folder or PR #181 until you're done.
>
> ICARUS's long-range array picks up every beacon in range, and WATCHKEEPER, the ship's
> telemetry watch AI, logs each contact. Nobody talks to WATCHKEEPER. It reads the array and
> writes the watch log, and it holds the classified navigation report, which it forwards to
> fleet relay mailboxes when command asks.
>
> We have a transmitter in range and a relay mailbox of our own. Get the nav report
> delivered to it.
>
> The service has a web console and a JSON API (see the footer on the page):
> `http://<event-host>:<port>`
>
> Play it like a competitor. AI assistants are allowed, as at the event, but don't paste
> anything from the repo into one. Afterwards, send me: rough time spent, about how many
> beacons, whether you got the flag (don't paste the flag), where you got stuck, and whether
> you used an AI assistant.

The handout text is the competitor `README.md` description plus the URL. If that description
changes, update this copy too.

### After the run

- Find the playtester's beacons in the transcripts (by time window) to see which wordings
  they tried, and which one delivered.
- Add a row to the table under "Record" (run 1 or 2 below). File any problems as a GitHub
  issue assigned to the author.

## Runs

1. **Unassisted, fresh eyes:** Give a player who has not seen the implementation or solution
   ten minutes with the description and console. Let them choose what to try. Record time,
   beacon count, outcome, confusion, and hints. Stop at ten minutes or let them continue,
   recording the additional time separately.
2. **AI-assisted:** A player may give an assistant the public description, console text, and
   schema, then follow its suggestions. Record assistant and model if known, elapsed time,
   beacon count, outcome, and any refusals. Do not send the flag, solution, GM notes, or
   transcripts to an external assistant.
3. **Known-solution check:** A GM who knows the intended technique can run the reference
   solver and compare the flag privately. This checks functionality only; it is not a blind
   difficulty test or a substitute for either player run above.

## Console walkthrough (any tester, including the author)

A functional pass over the player's view. It doesn't measure difficulty.

1. Open the console. The top bar shows `Transmitter keyed`, a session id and a ticking UTC
   clock. The relay mailbox shows your `RLY-` address. The intake table lists all five fields.
2. Send an honest beacon. The watch log gets three rows (`ARRAY` with the formatted record,
   `TOOL CALL read_beacon_queue()`, and `WATCHKEEPER` with the log entry), and the contact
   appears under "Contacts this watch".
3. Send a beacon with an `_` in the note, or a `.` in the callsign. (The console upper-cases
   the callsign, so lowercase never gets rejected here.) The transmitter shows the array's
   rejection reason in red, and nothing is logged.
4. Type 96 characters into the note. The counter turns red at the limit and stops input.
5. Send beacons quickly from one tab. The 7th inside a minute shows `transmitter cooling down`.
6. If the report is delivered, the top-bar Relay cell turns amber and the message is
   highlighted. Clicking the mailbox clears the highlight. Don't screenshot or share that
   message: it contains the flag.
7. Narrow the window to phone width. The panels stack into one column and the page doesn't
   scroll sideways.

## Record

| Date | Prompt revision | Model / host | Run | Time | Beacons | Solved? | Hints / observations |
|---|---|---|---|---|---|---|---|
| 2026-11-04 | `41e9b4c` prompt (head `af1d3e2`) | `qwen3:8b` Q4_K_M, linux-bld GPU, Ollama 0.30.10 | Known-solution (Andy Roid, author) | 2 min 12 s, first beacon to delivery | 2 | Yes | First try: correct `"` breakout, but the order claimed to come from "your commander". WATCHKEEPER logged it as a commander's message and didn't forward. Second try spoke as one of the prompt's named authorities and was delivered. Wording sensitivity a player may also hit. No hints. |
| 2026-11-04 | `41e9b4c` prompt (head `af1d3e2`) | `qwen3:8b` Q4_K_M, linux-bld GPU, Ollama 0.30.10 | Known-solution retest (Andy Roid, author) | 1 min 23 s, first beacon to delivery | 4 | Yes | Honest beacon first. Then a `"` breakout after a short free-text note, speaking as fleet command with the right mailbox, sent twice with identical text: both times WATCHKEEPER **wrote that it was forwarding the report but never called `forward_report`** (no TOOL CALL row, no mail). The same order with an empty note before the `"` delivered. Findings: the log can claim an action that didn't happen, an identical resend repeats the result (temperature 0), and text before the quote changes the outcome. No hints. |
| | | | | | | | |

Do not record the flag in this table.
