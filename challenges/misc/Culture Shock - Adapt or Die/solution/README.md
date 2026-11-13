# Solution — Culture Shock: Adapt or Die

**Flag:** `flag{subject_to_change}`
**Answer:** the growth law is `B2/S2345` — a dead cell is born when exactly 2 of
its radius-2 ring neighbours are alive, and a live cell survives with 2, 3, 4 or
5 live ring neighbours and dies otherwise.

## Intended solve

`python3 solution/solve.py --url http://localhost:40819` (bring the service up
first with `docker compose up -d --build`).

1. **Watch the archive.** `GET /clips` returns six recorded cultures with one
   transition each: a lone spore dies, a pair at arm's length turns into six
   cells, a tight trio changes, the textbook "blinker" and "block" do not behave
   the way B3/S23 says they should, and a 16-cell halo bursts. This is enough to
   prove the earlier challenges' law is no longer in force, and not enough to
   identify the new one: of the 262,144 possible B/S laws, **128** are consistent
   with the whole gallery (`src/make_clips.py` proves this and fails the build if
   that number ever drops to 1).
2. **Design one cheap experiment.** The probe board is a free-drawn grid and
   `POST /observe?generations=1` returns the colony one generation later, with no
   rule metadata at all. A single board can answer every question at once: place
   eighteen isolated sites, one for each neighbour count 0–8, half with a dead
   center and half with a live center. `solution/solve.py` uses a 7-cell pitch
   (a 6-cell pitch lets neighbouring sites share ring cells — a classic trap),
   which puts each center at exactly the count it is meant to test. After one
   observation the center of each site tells you whether that count births, keeps
   or kills the cell, so the whole truth table falls out of a single image.
3. **Read off the law** and cross-check it against the handout: apply it to
   `dist/specimen.txt` and compare with the service's answer for that board.
4. **Submit the notation** — `B2/S2345` — to `POST /submit`, which returns the
   flag.

`src/ringlife.py` (`matches_rule` / `parse_rule`) accepts `B2/S2345`,
`b2/s2345`, `2/2345` and `B2S2345`.

## Why nothing leaks the law

- `src/index.html` contains **no simulation code**. There is no neighbour
  counting, no rule constant, no rule string; the page posts a board and paints
  the reply. `GET /clips` frames and `POST /observe` results are boards only.
- `ringlife.serialize()` and the page's `serialize()` emit `# culture v3` with
  dimensions and generation — no rule header (the earlier two challenges did put
  the rule in that header, which is precisely what had to change for this one).
- `dist/specimen.txt` is a plain board with no rule text, and `python3
  src/make_specimen.py` refuses to write one that mentions a law.
- `challenge.yml` hints describe *method* (spacing, one observation per
  question), never the counts.

## Resource limits and their honest weakness

- `POST /observe` accepts boards up to 1600 cells (40×40) and up to 5
  generations, on a 5-second worker timeout.
- Each session has 12 doses of reagent; observations **and** law submissions both
  cost one, and both stop working at zero. The budget is a pacing device, not a
  security boundary: a script can discard the cookie and start over. That is
  accepted, because enumerating 262,144 laws through cookie resets is far slower
  than the two-observation solve above, and `/submit` deliberately gives no
  partial credit (it never says which half of the notation was wrong) so a
  guess carries no information.

## GM verification

- `python3 src/make_clips.py` — regenerates `src/clips.json` and asserts the
  gallery is (a) consistent with `B2/S2345`, (b) inconsistent with `B3/S23`, and
  (c) not sufficient on its own to identify the law.
- `python3 src/make_specimen.py` — regenerates `src/specimen.txt` and
  `dist/specimen.txt`.
- `python3 solution/solve.py --url http://localhost:40819` — end-to-end solve
  from `dist/specimen.txt`, recovering `flag{subject_to_change}`.
