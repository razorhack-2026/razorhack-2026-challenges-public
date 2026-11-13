# High Value Deposit

**Category:** Cryptography
**Difficulty:** Medium
**Author:** WALL-D

## Description (what the competitor will see)

See [../README.md](../README.md) and `description` in [../challenge.yml](../challenge.yml).

## Files Provided

None. Hosted on THE-DRILL: `ssh -p 2222 'TEAM#XX@<host>'`, unit 2 (DCU Dog-02). Locked until the
team mines Termite-01 (Level 1).

## Flag

`flag{H!9h-V@1u3-Emp10y33!}`

## Solution

Same puzzle as Level 1, but the nonce is one character longer and the lockout is 15 seconds:

    BLOCK_DATA   : DCU-07|SHAFT:K-5|BLOCK:000418|PREV:908cb5|NONCE:???????
    DEPOSIT_SHAPE: c0cf8ef4c7e6abf7152d5f0f4be3a08eed44ac7a8a7add6a9135c1af376c1064

(`PREV:908cb5` is the first 6 characters of Level 1's target hash, chaining the blocks.)

1. **Read the rules.** 7 hex characters gives 16^7 = 268,435,456 candidates, 16 times Level 1.
2. **Brute-force offline.** The Level 1 approach still works but is slower: about 2 minutes
   single-threaded. Splitting the search across cores, or hashing the shared prefix once and
   copying the hash state for each nonce, brings it down to a few seconds.
3. **Submit.** Enter `72c4f9a` at `ENTER KEY>`. The unit prints the flag and powers on Mole-03.

## Solve Script

[miner_level2.py](miner_level2.py) (single-threaded, block and target as defaults):

    python3 miner_level2.py
    # Searching 268,435,456 candidates (length 7, charset '0123456789abcdef')...
    # FOUND nonce: 72c4f9a  (120,344,475 tries, 117.687s)

Mole-03's multi-core solver (`REAL_DEAL.py`, added with that level's PR) also solves this level in
about 4 seconds on 16 threads. Paste the two lines above when it prompts.

Verified on 2026-11-02 from this branch: built THE-DRILL from `../Remote-Mining/` with
`docker compose up -d --build`, logged in over SSH as `TEAM#01`, confirmed Dog-02 was `[LOCKED]`
until Termite-01 was mined, then ran `python3 solution/miner_level2.py` and entered its nonce.
Dog-02 printed the flag in `challenge.yml` and showed `[MINED]` for TEAM#01 only.

## Techniques / Tags

`sha256`, `proof-of-work`, `brute-force`, `parallelization`

## Setup / Deployment Notes

### Where everything is

High Value Deposit has no server of its own. It runs on **THE-DRILL**, the SSH server that hosts
all three KALIUM levels, which was added by the Remote Mining PR. On this branch:

| File | What it is | Added by |
|---|---|---|
| `challenges/cryptography/High-Value-Deposit/challenge.yml`, `README.md`, `solution/` | This challenge's metadata, competitor text, solver and writeup | **This branch** |
| `challenges/cryptography/Remote-Mining/src/crypto_level2.py` | **The Dog-02 unit itself** (block, target hash, flag) | **This branch** |
| `challenges/cryptography/Remote-Mining/THE-DRILL/`, `docker-compose.yml`, `src/crypto.py` | THE-DRILL server and Termite-01 (Level 1) | Remote Mining branch |

The Dog-02 unit file is under `Remote-Mining/src/`, not `High-Value-Deposit/src/`, because THE-DRILL
builds every unit from that one folder (see `Remote-Mining/THE-DRILL/Dockerfile`). That's why
this folder has no `src/` or `docker-compose.yml`.

### Do I need to clone Remote Mining first?

**No.** This branch, `challenges/crypto/High-Value-Deposit`, is built on top of
`challenges/crypto/Remote-Mining` (a stacked PR), so it already contains everything from Remote
Mining. One clone and one checkout gives you the server, Termite-01 and Dog-02. Don't check out
the Remote-Mining branch to test this: that branch has no `crypto_level2.py`, so Dog-02 shows
`[OFFLINE]` there.

The only ordering rule is for merging: merge the Remote Mining PR first, then this one.

### Testing it, step by step

You need Docker with the Compose plugin running (`sudo systemctl start docker`), an SSH client and
Python 3.

1. **Get this branch** (skip the clone if you already have the repo):

       git clone <repo-url> razorhack-2026
       cd razorhack-2026
       git fetch origin
       git checkout challenges/crypto/High-Value-Deposit

2. **Confirm Dog-02's unit is there.** Both files should be listed:

       ls challenges/cryptography/Remote-Mining/src/
       # crypto.py  crypto_level2.py

3. **Start THE-DRILL.** All docker commands run from the Remote Mining folder, because that's where
   the compose files are:

       cd challenges/cryptography/Remote-Mining
       docker compose up -d --build
       docker compose logs -f    # wait for "Server listening on 0.0.0.0 port 22", then Ctrl+C

   If a THE-DRILL server is already running on this machine with event data, stop here and use
   the dev deployment (step 6) instead. `docker compose down -v` wipes all team progress.

4. **Log in as a team** (any account from `THE-DRILL/teams.txt`; TEAM 1's password is
   `mole-team-01`):

       ssh -p 2222 'TEAM#01@localhost'

   The Access Console should list Termite-01 `[ONLINE]`, Dog-02 `[LOCKED]` and Mole-03 `[OFFLINE]`
   (Mole-03 comes with its own PR).

5. **Unlock Dog-02 by solving Level 1, then solve Level 2.** In a second terminal, from
   `challenges/cryptography/`:

       python3 Remote-Mining/solution/miner.py              # ~10 s, prints Termite-01's nonce
       python3 High-Value-Deposit/solution/miner_level2.py  # ~2 min, prints Dog-02's DIS

   In the SSH session, choose unit 1 and enter the first nonce. You're returned to the console, and
   Dog-02 is now `[ONLINE]`. Choose unit 2 and enter the DIS. Dog-02 prints the flag (compare it with
   `challenge.yml`) and shows `[MINED]`.

6. **Shortcut: test Dog-02 without solving Level 1.** Use the dev deployment, which runs on its own
   port and progress volume, so it doesn't touch a real server:

       cd challenges/cryptography/Remote-Mining
       docker compose -f docker-compose.dev.yml up -d --build
       ssh -p 2223 'TEAM#AA@localhost'      # password: pass

   At the console menu, type the cheat code from `THE-DRILL/dev/code.txt`. All units unlock, so you
   can go straight to unit 2. The dev server is reachable only from the machine it runs on.

7. **Clean up:** `docker compose down -v` (or `docker compose -f docker-compose.dev.yml down -v`)
   from `challenges/cryptography/Remote-Mining/`.

Accounts, resets, host keys and the pre-event checklist are in
[Remote-Mining/THE-DRILL/DEPLOYMENT.md](../../Remote-Mining/THE-DRILL/DEPLOYMENT.md). This challenge
has no `dist/` files; competitors only need SSH.

## Known Issues / Notes

- Still easy for an AI assistant. The step up is in compute, not in insight.
- The block is the same for every team, so the nonce could be shared.
