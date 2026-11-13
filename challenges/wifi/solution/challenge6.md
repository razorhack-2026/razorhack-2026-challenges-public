# DB Challenge 4 - The Heap Never Let Go

**Category:** Forensics
**Difficulty:** Hard
**Author:** Lt. Rico Kopernicus

## Description

Something is still running against the database.  Maybe some runtime crashed on the flight computer?  Some service worker never closed its connection? Find out what's happening.

## Flag

`flag{d34d_tupl3s_t3ll_t4l3s}`

(Continues story seeded in the black box bonus challenge)  
The sealed pod DELTA-7 launched under the forged priority directive itself, so
its `manifest_code` is the authorization that order carried - the one line left
aboard that could disprove RPC_CENTCOM's authorship, which is exactly why MH-2
was sent to delete it. The row was INSERTed into `evac_manifest` and then
DELETEd, both with statement logging suppressed - so unlike DB Challenge 1, it
is **not** in the server log. It survives only as a dead heap tuple, kept from
being vacuumed/pruned by a long-lived idle-in-transaction session that pins the
xmin horizon. Recovery is a raw heap-file read via `pg_read_binary_file`.

## Solution

1. Reach the DB and get the `icarus_svc` role exactly as in DB Challenge 1
   (guest -> `ops_config` creds -> reconnect as `icarus_svc`).
   ```bash
   psql -h 192.168.1.11 -U icarus_svc -d icarus_core   # password from ops_config: Sv3c-L0gAud1t-9f21
   ```
2. Look at the manifest. It reads back as routine pods only - MH-2 cleared the
   sealed row - which is the whole hook:
   ```sql
   SELECT * FROM evac_manifest;   -- routine pods only; the sealed one is gone
   ```
3. Find the anomaly. `icarus_svc` is in `pg_read_all_stats`, so it can see the
   stuck maintenance session and, crucially, that it is holding an old snapshot
   (`backend_xmin` is set):
   ```sql
   SELECT pid, state, backend_xmin, application_name, query
   FROM pg_stat_activity
   WHERE state = 'idle in transaction';
   -- application_name = manifest_purge_worker, backend_xmin = <old xid>,
   -- query = 'MH-2 manifest hygiene - purge worker stalled mid-directive'
   ```
   A transaction stuck open with a held `backend_xmin` is the textbook reason
   deleted rows are never vacuumed - the dead tuples are still on disk.
4. Locate the table's heap file (no special privilege needed for the path):
   ```sql
   SELECT pg_relation_filepath('evac_manifest');   -- e.g. base/16384/16453
   ```
5. Read the raw heap page. `pg_read_file` (text) chokes on the NUL bytes in a
   heap page under UTF8, so use the binary reader (granted to `icarus_svc`) and
   render it printable:
   ```sql
   \pset pager off
   SELECT encode(pg_read_binary_file('base/16384/16453'), 'escape');
   ```
   The DELETEd tuple's bytes are still in the page. Its `manifest_code` column
   holds the flag; the `note` shows the `EVAC-DELTA-7 sealed - MH-2 hygiene
   purge pending` marker next to it.

   Grep-style shortcut:
   ```sql
   SELECT (regexp_matches(
             encode(pg_read_binary_file(pg_relation_filepath('evac_manifest')), 'escape'),
             'flag\{[a-z0-9_]+\}'))[1];
   ```
6. Recover the flag:
   ```
   flag{d34d_tupl3s_t3ll_t4l3s}
   ```

## Why it's recoverable (and how it's kept alive)

- The "stalled purge worker" is a holder session that runs `BEGIN ISOLATION
  LEVEL REPEATABLE READ; SELECT pg_current_snapshot();` and then sits
  idle-in-transaction forever. Its
  registered snapshot holds `OldestXmin` below the DELETE's xid, so the deleted
  tuple is `RECENTLY_DEAD` (not `DEAD`) - VACUUM and `heap_page_prune_opt` both
  leave it alone. (`postgres_startup.sh` starts a few redundant holders and waits
  for `backend_xmin` before seeding.)
- Backstop: `evac_manifest` is created `WITH (autovacuum_enabled=false)` and kept
  to a handful of short rows. `heap_page_prune_opt` won't even attempt a page with
  more than ~10% free space, so a sparse page survives even if every holder dies.
  **Do not bulk-load this table** - a near-full page re-enables pruning.
- The seed (`heap.sql`) runs with `log_statement='none'` (+ `log_min_error_statement
  = panic`), so the flag never reaches `log/postgresql.log`. That is what makes
  this distinct from DB Challenge 1.
- `manifest_code`/`note` are `STORAGE PLAIN` and short, so the flag stays as
  contiguous, greppable ASCII in the page (no TOAST/compression scattering it).

## Deployment / Maintenance Notes

- There is no PGDATA volume, so `docker compose down && up --build` re-runs initdb
  + reseeds + reopens the holders cleanly. **Do not `docker restart` / `stop`+`start`
  the postgres container mid-competition**: that preserves the data dir but a fresh
  holder's snapshot post-dates the old DELETE, so the tuple would no longer be
  protected. The startup guard is content-based (re-seeds if the `EVAC-DELTA-7`
  sentinel is missing from the heap) so it self-heals, but reset with down/up.
- Keep `STOPSIGNAL SIGINT` on the image (postgres:16 default) - fast shutdown is
  what stops `docker stop` hanging on the idle holders.
- Second recovery path, deliberately not advertised to players: the INSERT's bytes
  also live in `pg_wal/*`, readable via `pg_read_binary_file`. So even a pruned
  heap page does not necessarily mean the challenge is broken.

## Techniques / Tags

`postgres`, `database`, `mvcc`, `dead-tuples`, `heap-forensics`, `vacuum`, `forensics`
