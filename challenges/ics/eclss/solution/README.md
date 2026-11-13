# ECLSS + Training Bay: GM notes

Staff only. Holds every flag and the disarm code. The full staff guide (the
puzzles, every value, hints) is `STAFF_GUIDE.md`. This page covers how the
set is deployed and checked at RazorHack.

## Layout

| Path | What |
|------|------|
| `../metadata/*.yml` | 22 CTFd challenges: `training-mb1..7`, `training-pl1..5`, `training-ig1..3`, `eclss-1..7`. All carry topic `instance:eclss` |
| `../dist/` | Player handouts. `training/REGISTER_MAP.md` and `training/TRAINING_LOGIC.st` are builder output, copied from `../src/training/student/` |
| `../src/` | The author's kit: builder, PLC programs (prebuilt in `build/`), Ignition projects and gateway config, the three event images (`images/`), `flags.json`, `training/training_flags.json` |
| `eclss/` | ECLSS solver `solve.py`, offline `mock_rig.py`, `SOLUTIONS.md`, `HINTS.md`, `SCORING.md` |
| `training/` | Training Bay solver `solve_training.py`, `SOLUTIONS.md`, `HINTS.md` |

## How it's hosted

**One copy per team, started from CTFd.** All 22 challenges share the topic
`instance:eclss`, so Start on any of them starts the team's one copy. It is a
Fargate task in the team's own security group, at
the rig host (localhost with docker compose), and only that team's Kali box can reach it. CTFd
fills `{host}` into each challenge's connection info.

The task runs the three images in `../src/images/` (see `../src/README.md`):
the ECLSS PLC on 502, the Training PLC on 5020, and Ignition on 8088. The task
definition is `eclss` in Razorhack-Infra `lib/challenges.json`.

- **Start:** the images are pulled first (Ignition is ~0.7 GB, trimmed to the
  three modules the rig uses: `src/images/ignition/Dockerfile`), then the PLCs
  answer within seconds and the HMI in about a minute. Tell teams to allow a
  few minutes.
- **Stop:** resets everything: a fresh ship (MaintSync re-armed, flags 3-7
  unpublished) and a fresh Training Bay. Points already scored stay in CTFd.
- **Expiry:** like every copy, it stops after `runHours` unless the team
  presses Start again to extend it.
- **The Ignition trial (2 h):** the gateway resets its own trial when it
  expires (`rh-entrypoint.sh`), so the HMI is down for at most ~30 s every
  2 hours. If a team reports "Trial Expired" for longer, check the task's
  `ignition` log for `trial-keeper` lines. Stop + Start always fixes it.
- **No passwords to manage.** Each copy's Ignition admin password is random and
  thrown away. The OpenPLC runtime APIs listen on `127.0.0.1` only.

## Deploy (once, then after any change here)

From Razorhack-Infra, after this folder is on `razorhack-2026` `main`:

```powershell
python tools/challenge_images.py build eclss
python tools/challenge_images.py push eclss
```

Then Admin -> RazorHack -> **Sync challenges** in CTFd. No flag secret is
needed: every flag is baked into the images.

## Health checks

Run against a copy (team 00's from CTFd, or a local `docker compose up -d
--build` in `../src/`). From `challenges/ics/eclss/`, on a box that can reach it:

```bash
pip install -r solution/eclss/requirements.txt
python solution/eclss/solve.py --host <host> --port 502 --code <disarm_code from src/flags.json>
python solution/training/solve_training.py --host <host> --port 5020 --gateway http://<host>:8088
python solution/eclss/mock_rig.py       # offline: a protocol mock of the ECLSS PLC on 127.0.0.1:1502
```

- **`solve.py`:** disarms MaintSync, restores the ship and captures flags 1
  and 3-7. It takes up to ~4 minutes, mostly CO2 recovery.
- **`solve_training.py`:** captures all 12 Modbus/OpenPLC flags, locks IG3
  on the PLC, finds IG1's name on `/system/gwinfo`, and checks them against
  `src/build/training/flags_all.json`.
- **In a browser:**
  - `/data/perspective/client/eclss/crew-manifest` shows ECLSS 2.
  - `/maint` shows the disarm code, but not a flag.
  - The Training HMI has the hidden IG2 label (developer tools, Elements tab, search `flag{`).
  - Typing 1420 there shows IG3 for 30 s.

Both solvers solve everything. On Fargate, Stop and Start the copy afterwards.
Locally, run `docker compose up -d --force-recreate`.

## Changing flags

1. Edit `src/flags.json` and/or `src/training/training_flags.json`. Each flag
   must be 32 characters or fewer.
   - If `gateway_name` changes, also change `IGN_GATEWAY_NAME` in
     `src/images/ignition/Dockerfile`. It is IG1's flag.
2. `docker compose run --rm builder` in `src/` (needs internet: it clones
   STruC++ and runs `npm ci`). All 35 unit tests must pass.
3. Copy `src/training/student/REGISTER_MAP.md` and `TRAINING_LOGIC.st` to
   `dist/training/`.
4. Update `flags:` in the matching `metadata/*.yml`. The ymls hold the kit's
   default values.
5. Merge, then build and push the images (above).

## Decisions and fixes (review 2026-11-04)

- **Flags 3-5 had to be earned, not free.** The cabin used to start in
  range, so on every PLC start the objective bits set on the first scan and
  the three flag blocks were published before anyone touched it.
  - The ship now starts already out of spec: O2 19.0 %, CO2 6000 ppm,
    28.5 C, with bed A saturated.
  - With MaintSync armed it can't drift back into range on its own.
  - Unit tests check both that an untouched ship earns nothing in 10 minutes
    and that fixing O2 and temperature still earns their bits inside one
    20 s window.
- **Training Bay windows are deliberate (2026-11-05).** As in the kit, each
  timed Training Bay challenge re-arms 15-30 s after a solve (MB4, MB7, PL1-5,
  IG3), so teams have to grab the flag promptly, which rewards scripting the
  read. A same-day change that kept them solved until a bay reset (coil 31
  and a RESET TRAINING BAY button) was rolled back.
- **ECLSS 2's hint pointed at guessing (2026-11-05).** "Think about what a
  retired console might be named" doesn't lead to `crew-manifest`. The page
  is findable without guessing, because the browser downloads the project's
  page list, `/maint` included. The hint now points there (developer tools,
  Network tab), and ECLSS 6 says its console is found the same way.
- **ECLSS 3-5 say where to look, and 4 says a one-off fix won't hold
  (2026-11-05).** No register map is handed out (matching the HMI's readouts
  to a holding-register sweep is the skill). The hints now say so, say the
  writable registers start at 1024 as in the Training Bay, and say each
  flag appears near the ECLSS 1 banner. Two unit tests check that one fix to
  AUTO never clears CO2 while MaintSync is armed, and that putting AUTO back
  after every re-pin does (without disarming). The staff guide used to say
  all of 3-5 could be caught in a 20 s gap, which isn't true for CO2.
- **Flag 6 is only on Modbus.** `/maint` used to print it next to the disarm
  code, so finding the page was enough. It now gives only the code. The flag
  appears at HR1204 once the code is written to HR1030.
- **Scoring:** uniform dynamic scoring (500), not the author's 25-225 weights.
  The weights are noted in each yml header and in `eclss/SCORING.md`.
- **Hints:** the author's three hint tiers per challenge are in
  `eclss/HINTS.md` and `training/HINTS.md`. None are in the ymls. The sync only
  creates hints on a challenge's first import.
