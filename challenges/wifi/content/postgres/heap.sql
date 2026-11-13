-- Icarus Bridge - evac_manifest heap-recovery seed (DB Challenge 4).
--
-- Story: the abandon-ship directive that emptied the Icarus was forged, and a
-- second directive rode in behind it on the same bus - a routine-looking
-- "manifest hygiene" order (MH-2) telling the ship to scrub sealed pod records
-- before the loss report went home. The Bridge's own purge worker obeyed. It
-- got as far as DELTA-7 and then stalled with its transaction still open,
-- which is the only reason the row is still on disk.
--
-- Replayed post-start over loopback as postgres, AFTER a holder transaction is
-- already pinning the xmin horizon (see postgres_startup.sh). Unlike history.sql
-- (DB Challenge 1), statement logging is SILENCED for this session so the flag
-- never lands in log/postgresql.log - the only place it survives at rest is the
-- raw heap file, recovered via pg_read_binary_file.
--
-- Each INSERT/DELETE below is its own autocommit transaction, so the deleted
-- tuple gets xmin != xmax (sidesteps the same-transaction prune special cases).
-- Keep this file SPARSE: a near-full page would let a plain SELECT prune the
-- dead tuple once the horizon advances. A handful of short rows only.

SET log_statement = 'none';
SET log_min_duration_statement = -1;
-- Without this, any statement that raised an ERROR would be echoed verbatim to
-- the log (log_min_error_statement defaults to 'error') - leaking the flag.
SET log_min_error_statement = panic;

-- Live manifest rows (survive the purge; make SELECT * look gap-toothed/real).
INSERT INTO evac_manifest (pod, passenger, manifest_code, note) VALUES ('POD-01', 'A. Reyes', 'MC-1007', 'boarding confirmed');
INSERT INTO evac_manifest (pod, passenger, manifest_code, note) VALUES ('POD-02', 'K. Ilori', 'MC-1042', 'boarding confirmed');
INSERT INTO evac_manifest (pod, passenger, manifest_code, note) VALUES ('POD-04', 'T. Novak', 'MC-1090', 'standby');

-- The sealed record MH-2 was sent to erase: DELTA-7 launched under the priority
-- directive itself, so its manifest_code is the authorization the forged order
-- carried - the one line aboard that could disprove RPC_CENTCOM's authorship.
-- Inserted, then purged. The DELETE clears the live row, but the holder's old
-- snapshot keeps the dead tuple RECENTLY_DEAD, so its bytes stay in the heap.
-- 'EVAC-DELTA-7' is a non-flag sentinel the startup script probes for to decide
-- whether to (re)seed.
INSERT INTO evac_manifest (pod, passenger, manifest_code, note) VALUES ('DELTA-7', 'SEALED', 'flag{d34d_tupl3s_t3ll_t4l3s}', 'EVAC-DELTA-7 sealed - MH-2 hygiene purge pending');
DELETE FROM evac_manifest WHERE pod = 'DELTA-7';

-- Boarding carried on; the worker never came back for the rest of the list.
INSERT INTO evac_manifest (pod, passenger, manifest_code, note) VALUES ('POD-05', 'R. Haddad', 'MC-1120', 'boarding confirmed');

-- Flush dirty buffers so the on-disk file pg_read_binary_file reads actually
-- contains the (dead) tuple bytes; without this the player could read a
-- tuple-less page.
CHECKPOINT;
