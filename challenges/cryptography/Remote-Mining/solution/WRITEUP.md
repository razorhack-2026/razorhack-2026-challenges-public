# Remote Mining

**Category:** Cryptography
**Difficulty:** Easy 
**Author:** WALL-D

## Description (what the competitor will see)

See [../README.md](../README.md) and `description` in [../challenge.yml](../challenge.yml).

## Files Provided

None. Hosted on THE-DRILL: `ssh -p 2222 'TEAM#XX@<host>'`, unit 1 (DCU Termite-01).

## Flag

`flag{M!^!n9_Th3_Futur3}`

## Solution

DCU Termite-01 is a small proof-of-work puzzle. The unit prints:

    BLOCK_DATA   : DCU-07|SHAFT:K-4|BLOCK:000417|PREV:9f3a1c|NONCE:??????
    DEPOSIT_SHAPE: 908cb5e240ae02fa000a95cf965ebd7c41b63ca739d78c6e75c616dee261a008

and asks for the 6-character DIS (drill input sequence) such that
`sha256(BLOCK_DATA + DIS) == DEPOSIT_SHAPE`, where the DIS uses the charset `0123456789abcdef`.

1. **Read the rules.** The banner gives the formula, the length (6) and the charset (hex), so the
   search space is 16^6 = 16,777,216 candidates.
2. **Notice guessing at the console won't work.** Each wrong key locks the console for 5 seconds,
   so the brute force has to happen offline.
3. **Brute-force locally.** Append every 6-character hex string to the block data, SHA-256 it and
   compare it with the target. Single-threaded Python finds it in about 11 seconds.
4. **Submit.** Enter the nonce `b0a7e1` at `ENTER KEY>`. The unit prints the flag, marks
   Termite-01 as mined for the team, and powers on Dog-02.

## Solve Script

[miner.py](miner.py) has the block and target as defaults:

    python3 miner.py
    # Searching 16,777,216 candidates (length 6, charset '0123456789abcdef')...
    # FOUND nonce: b0a7e1  (11,577,314 tries, 11.298s)

Verified on 2026-11-02 from this folder: `docker compose up -d --build`, logged in over SSH as
`TEAM#01`, ran `python3 solution/miner.py` and entered its nonce in Termite-01. The unit printed the
flag in `challenge.yml`, showed as `[MINED]` for TEAM#01 only, and Dog-02/Mole-03 showed `[OFFLINE]`.

## Techniques / Tags

`sha256`, `proof-of-work`, `brute-force`

## Setup / Deployment Notes

- Runs on THE-DRILL, the SSH server shared by all three levels. It lives in this folder because
  Termite-01 is the first level. Deployment, accounts, resets and the pre-event checklist are in
  [THE-DRILL/DEPLOYMENT.md](../THE-DRILL/DEPLOYMENT.md).
- The image is built from this folder: the units come from `src/` and the server from `THE-DRILL/`.
  `src/crypto.py` is Termite-01. Dog-02 and Mole-03 show `[OFFLINE]` until their PRs add
  `src/crypto_level2.py` and `src/crypto_level3.py`.
- No `dist/` files; the competitor only needs SSH.

Run these from this challenge folder (`challenges/cryptography/Remote-Mining/`):

- 0. Reset the server with `docker compose down -v`. If the server is already running during the event with user data, **SKIP THIS STEP**
- 1. Start the server with `docker compose up -d --build`
- 2. Connect to the server (port 2222) with a team's username/password
  - Players use their team number and the password in `THE-DRILL/teams.txt`; TEAM 1 connects with `ssh -p 2222 'TEAM#01@<host>'` and password `mole-team-01`
  - Devs test on the separate dev deployment instead: `docker compose -f docker-compose.dev.yml up -d --build`, then `ssh -p 2223 'TEAM#AA@localhost'` (or `TEAM#BB`), password `pass`. The dev deployment is reachable only from the host machine, and only TEAM#AA/TEAM#BB (from `THE-DRILL/dev/teams.txt`) exist there in addition to the real teams


## Known Issues / Notes

- By design this level is easy: an AI assistant will write a working brute-forcer immediately.
  The difficulty ramps up in Levels 2 and 3.
- The block is the same for every team, so a team could share the nonce. The same goes for the flag.
- Teams can run Python on THE-DRILL itself, so a miner on the server's CPU is possible
  (see DEPLOYMENT.md §7 for capping CPU).
