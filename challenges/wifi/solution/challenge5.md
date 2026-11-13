# DB Challenge 3 - Black Box (Easter Egg)

**Category:** Forensics
**Difficulty:** Easy (hidden / bonus)
**Author:** Lt. Rico Kopernicus

## Description
Planes usually have a black box logging everything that happens on them. See if you can find something like that in the Icarus bridge.

## Flag

`flag{fl3w_t00_cl0s3_t0_th3_sun}`

Stored at rest in a plain-text file **outside** the database data directory:
`/opt/icarus/blackbox.log` - a mirror of the Icarus core event recorder covering
the night the crew left. The ship was a RazorPowerCo deep-prospecting hull on its
home leg when a priority RPC_CENTCOM directive ordered ABANDON SHIP, ALL
HANDS. The directive carried a valid fleet header and a malformed origin block:
it was forged. Nothing was ever wrong with the Icarus - hull, reactor and air were all
nominal - so the crew podded off a perfectly good ship, the fleet wrote her off
as a navigational loss, and she has been flying empty and intact ever since. The
tail of the log, 1144 days on, records an unauthenticated session arriving on the
maintenance channel with the same malformed origin block: the operator who
emptied the ship coming back to take it. That is the Dr. Rootkit hand-off - it
explains why the players are talking to Icarus systems at all, and it gives away
nothing about the other challenges.

## Solution

1. Get the `icarus_svc` role exactly as in DB Challenge 1 (guest -> `ops_config`
   creds -> reconnect as `icarus_svc`). `icarus_svc` is a member of
   `pg_read_server_files`, which allows reading **arbitrary absolute paths** the
   `postgres` OS user can read - not just files under the data directory.
   ```bash
   psql -h 192.168.1.11 -U icarus_svc -d icarus_core   # password from ops_config
   ```
2. Explore the filesystem the same way you found the log, but wander outside PGDATA:
   ```sql
   SELECT pg_ls_dir('/');            -- notice: opt
   SELECT pg_ls_dir('/opt');         -- icarus
   SELECT pg_ls_dir('/opt/icarus');  -- blackbox.log
   ```
3. Read it:
   ```sql
   \pset pager off
   SELECT pg_read_file('/opt/icarus/blackbox.log');
   ```
   The flag is on a `[NOTE]` line, directly under the crew's rebuttal of the
   fleet's "navigational" loss finding.

## Techniques / Tags

`postgres`, `database`, `file-read`, `forensics`, `easter-egg`
