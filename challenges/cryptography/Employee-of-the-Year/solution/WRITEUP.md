# Employee of the Year - Kalium Collector

**Category:** Cryptography
**Difficulty:** Hard
**Author:** WALL-D

## Description (what the competitor will see)

See [../README.md](../README.md) and `description` in [../challenge.yml](../challenge.yml).

## Files Provided

None. Hosted on THE-DRILL: `ssh -p 2222 'TEAM#XX@<host>'`, unit 3 (DCU Mole-03). Locked until the
team mines Dog-02 (Level 2).

## Flag

`flag{M0$t-V@1u!bl3-Ext4@ct04}`

## How the unit works

Mole-03 is a race between all teams, not a fixed puzzle:

- Every 30 minutes, on the hour and the half hour (container time zone, default
  `America/Chicago`), a new block is released with a fresh random 10-character hex nonce:

      BLOCK_DATA   : DCU-07|SHAFT:K-6|BLOCK:<random 6 digits>|PREV:<first 6 of last target>|NONCE:??????????
      DEPOSIT_SHAPE: <sha256 of block + nonce>

- The first team to submit the right DIS gets the flag and +1 on Mole-03's in-game scoreboard.
  The unit is then **sealed for everyone** until the next block.
- A wrong key locks the **whole team** out for 30 seconds, across all their connections.
- If nobody mines a block before it expires, its nonce is broadcast and a new block starts.

## Solution

1. **Size the problem.** 16^10 ≈ 1.1 trillion candidates against a 30-minute window. The
   multi-core Python miner from Level 2 runs at about 10 million hashes/s on 16 threads, so it
   would need about 14 hours on average. CPU Python won't win a round.
2. **Recognize the hash format.** `sha256(BLOCK_DATA + DIS)` is SHA-256 of salt followed by
   password, which is hashcat mode **1420** (`sha256($salt.$pass)`). The DIS is a 10-character
   lowercase-hex mask (`?h` x 10).
3. **Crack on a GPU.** When a block is released, copy the two lines and build a hashcat target.
   Hex-encode the salt, because the block data contains `:` (hashcat's separator):

       # target.txt: <DEPOSIT_SHAPE>:<hex of BLOCK_DATA without the ?s>
       python3 -c "import sys; print(sys.argv[2] + ':' + sys.argv[1].encode().hex())" \
           'DCU-07|SHAFT:K-6|BLOCK:123456|PREV:abcdef|NONCE:' '<DEPOSIT_SHAPE>' > target.txt
       hashcat -m 1420 -a 3 --hex-salt target.txt '?h?h?h?h?h?h?h?h?h?h'

   Estimate (not measured): around 10 minutes worst case on a laptop RTX 3050, since block plus
   nonce is 58 bytes, so each candidate takes two SHA-256 compressions. Desktop GPUs are much faster.
4. **Submit fast.** Enter the cracked DIS at `ENTER KEY>` before another team does. Only the
   winner of each block sees the flag.


## Solve Scripts

- [REAL_DEAL.py](REAL_DEAL.py): multi-core CPU miner. Paste the `BLOCK_DATA` and `DEPOSIT_SHAPE`
  lines and it reads the nonce length from the `?` count. It solves Levels 1–2 in seconds but is
  too slow for a 10-character Mole-03 block within one round.
- [miner_level3.py](miner_level3.py): single-threaded version (`--block`, `--target`; the
  length defaults to 10).
- The intended full-length solve is the hashcat command above.

Verified on 2026-11-02 from this branch, on THE-DRILL built from `../Remote-Mining/`:

- **Real settings** (`NONCE_LENGTH = 10`, `ROUND_SECONDS = 1800`): all three units started; Mole-03
  was `[LOCKED]` until Dog-02 (or the dev cheat), then showed a 10-character block with its
  30-minute release time, and `[0] SCOREBOARD` appeared.
- **Full solve with the DIS shortened to 6** (testing step 6 below, on a copy of the folder):
  `REAL_DEAL.py` found the DIS in 1.4 s; entering it printed the flag in `challenge.yml`, set
  TEAM#AA's score to 1 and sealed the unit. TEAM#BB, sitting in unit 3, received the
  "MINED BY TEAM#AA" broadcast, and the scoreboard ranked TEAM#AA first.
- **Not yet run:** the full 10-character solve with hashcat on a GPU (step 3 of the solution). The
  timing in step 3 is still an estimate.

## Techniques / Tags

`sha256`, `proof-of-work`, `gpu-cracking`, `hashcat`, `race`

## Setup / Deployment Notes

### Where everything is

Employee of the Year has no server of its own. It runs on **THE-DRILL**, the SSH server that
hosts all three KALIUM levels, which was added by the Remote Mining PR. On this branch:

| File | What it is | Added by |
|---|---|---|
| `challenges/cryptography/Employee-of-the-Year/challenge.yml`, `README.md`, `solution/` | This challenge's metadata, competitor text, solvers and writeup | **This branch** |
| `challenges/cryptography/Remote-Mining/src/crypto_level3.py` | **The Mole-03 unit itself** (rounds, scoreboard, flag) | **This branch** |
| `challenges/cryptography/Remote-Mining/src/crypto_level2.py` | Dog-02 (Level 2), which must be mined before Mole-03 unlocks | High Value Deposit branch |
| `challenges/cryptography/Remote-Mining/THE-DRILL/`, `docker-compose.yml`, `src/crypto.py` | THE-DRILL server and Termite-01 (Level 1) | Remote Mining branch |

The Mole-03 unit file is under `Remote-Mining/src/`, not `Employee-of-the-Year/src/`, because
THE-DRILL builds every unit from that one folder (see `Remote-Mining/THE-DRILL/Dockerfile`). That's
why this folder has no `src/` or `docker-compose.yml`.

Mole-03's settings are at the top of `Remote-Mining/src/crypto_level3.py`: `NONCE_LENGTH` (10),
`ROUND_SECONDS` (1800), `LOCKOUT_SECONDS` (30) and `FLAG`. Its state (scores, rounds and the
**current answer**) is saved in `/var/lib/dcu/unit3.json` inside the container, readable only by
the `drill` user.

### Do I need to clone Remote Mining or High Value Deposit first?

**No.** This branch, `challenges/crypto/Employee-of-the-Year`, is built on top of
`challenges/crypto/High-Value-Deposit`, which is built on top of `challenges/crypto/Remote-Mining`
(stacked PRs). It already contains everything from both. One clone and one checkout gives you the
server and all three units. Don't test from either of the other branches: neither has
`crypto_level3.py`, so Mole-03 shows `[OFFLINE]` there.

The only ordering rule is for merging: merge Remote Mining first, then High Value Deposit, then
this one.

### Testing it, step by step

You need Docker with the Compose plugin running (`sudo systemctl start docker`), an SSH client and
Python 3. Solving a full 10-character block also needs a GPU and hashcat; steps 6–7 show how to test
without one.

1. **Get this branch** (skip the clone if you already have the repo):

       git clone <repo-url> razorhack-2026
       cd razorhack-2026
       git fetch origin
       git checkout challenges/crypto/Employee-of-the-Year

2. **Confirm all three units are there:**

       ls challenges/cryptography/Remote-Mining/src/
       # crypto.py  crypto_level2.py  crypto_level3.py

3. **Start THE-DRILL** in the dev deployment, so you can skip Levels 1–2 with the cheat code. It
   runs on its own port and progress volume, so it doesn't touch a real server:

       cd challenges/cryptography/Remote-Mining
       docker compose -f docker-compose.dev.yml up -d --build
       docker compose -f docker-compose.dev.yml logs -f   # wait for "Server listening", then Ctrl+C

4. **Log in and open Mole-03:**

       ssh -p 2223 'TEAM#AA@localhost'      # password: pass

   At the console menu, type the cheat code from `THE-DRILL/dev/code.txt`. All units unlock and
   `[0] SCOREBOARD` appears. Choose unit 3. It shows the current block, the time the next block is
   released, and two lines to copy:

       BLOCK_DATA   : DCU-07|SHAFT:K-6|BLOCK:<6 digits>|PREV:<6 hex>|NONCE:??????????
       DEPOSIT_SHAPE: <64 hex>

   To test the real unlock path instead, log in as a normal team on the production deployment
   (`docker compose up -d --build`, port 2222) and mine Termite-01 and Dog-02 first. The Remote
   Mining and High Value Deposit writeups have those steps.

5. **Full-length solve (GPU).** Run the hashcat commands from "Solution" step 3 against the two
   lines, then enter the DIS at `ENTER KEY>` before the block expires. Mole-03 prints the flag
   (compare it with `challenge.yml`), adds 1 to your score, and seals the unit for everyone until
   the next block. A second login (e.g. `TEAM#BB`) sitting in unit 3 sees the
   "MINED BY TEAM#AA" announcement.

6. **Quick solve without a GPU: shorten the DIS for testing only.** In
   `Remote-Mining/src/crypto_level3.py`, change `NONCE_LENGTH = 10` to `NONCE_LENGTH = 6`. Then
   rebuild **with a reset**. The reset matters: the block that's live when you rebuild keeps its
   10-character answer, so it can't be solved with the new length.

       docker compose -f docker-compose.dev.yml down -v
       docker compose -f docker-compose.dev.yml up -d --build

   Log in again, run the cheat code, open unit 3, and run the CPU solver from `challenges/cryptography/`:

       python3 Employee-of-the-Year/solution/REAL_DEAL.py   # paste the two lines; ~1 s for 6 characters

   Enter the DIS it prints. Mole-03 prints the flag, the score goes to 1, and the unit shows
   `SEALED by TEAM#AA` until the next block.

7. **Undo the test change before committing:** set `NONCE_LENGTH` back to `10`
   (`git checkout -- Remote-Mining/src/crypto_level3.py` does this), then reset again with
   `down -v` / `up -d --build`.

8. **Clean up:** `docker compose -f docker-compose.dev.yml down -v` from
   `challenges/cryptography/Remote-Mining/`.

**Before the event:** do a full reset on production (`docker compose down -v && docker compose up
-d --build` from `Remote-Mining/`) so test rounds and scores are gone. Accounts, resets, host keys
and the pre-event checklist are in
[Remote-Mining/THE-DRILL/DEPLOYMENT.md](../../Remote-Mining/THE-DRILL/DEPLOYMENT.md). This challenge
has no `dist/` files; competitors only need SSH.

## Known Issues / Notes

- The flag is the same for every block, so a team that wins once can share it. CTFd only scores
  it once per team; the in-game points per block aren't reflected in CTFd.
- Teams without a GPU have no realistic path to winning a block. Mention that in the description,
  or accept it as part of the "hard" tier.
- Only one team can win each round. With 30-minute rounds over the event, there are a limited
  number of flags to go around, so many teams may never solve it.
- Shared team passwords let one team lock out another (`Remote-Mining/THE-DRILL/DEPLOYMENT.md` §6).
  Every team in `THE-DRILL/teams.txt` already has its own password.
