# Challenge Name

**Category:** Web / Pwn / Crypto / Forensics / Rev / Misc
**Difficulty:** Training / Easy / Medium / Hard / Insane
**Author:** Name

## Description (what the competitor will see)

The text players see on the CTF platform. Don't worry too much about this,
but do try to keep the challenges space-adjacent.


## Files Provided

- `handout.zip` — what the player downloads
- (or) Hosted at `nc challs.razorhack.io 1337`

## Flag

`flag{example_flag_here}`

## Solution

Step-by-step walkthrough of the intended solve. Be specific enough that
another GM can follow along and verify the challenge works.

1. First step — what the player notices or does first
2. Second step — the key insight or technique
3. Third step — recovering the flag

Include code snippets, commands, or screenshots where helpful.

Don't worry about every solve case; focus on your intended solve here.

## Solve Script

See `solution/solve.py` (or wherever). The script should run end-to-end
against the deployed challenge and print the flag.

## Techniques / Tags

`sql-injection`, `blind-injection`, `time-based`

## Setup / Deployment Notes

Anything a deployer needs to know:
- Docker: `docker compose up` from this directory
- Environment vars needed
- Resource requirements (memory, ports, etc.)
- Anything fragile or non-obvious

If you don't know how to deploy your challenge, reach out in the Discord and we will give you resources and advice. 

## Known Issues / Notes

Optional. Unintended solves discovered during review, edge cases, things
to watch for during the event.