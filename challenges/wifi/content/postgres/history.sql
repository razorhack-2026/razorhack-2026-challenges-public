-- Icarus Bridge - operator/maintenance activity replayed AFTER the real
-- server is up, so every statement below is captured by log_statement='all'
-- in log/postgresql.log. This is the ONLY place the flag material exists at
-- rest: the sensitive rows/columns are removed again before the window ends,
-- so they survive only in the server log.
--
-- The shell guard in postgres_startup.sh runs this file at most once per data
-- directory (see the __seed_state marker at the end).

-- --- routine reads / shift handover -----------------------------------------
SELECT callsign, name, role FROM crew ORDER BY clearance DESC;
SELECT bay, charge_pct, status FROM power_cells WHERE status <> 'nominal';

UPDATE power_cells SET charge_pct = 41, status = 'degraded' WHERE bay = 'B1';
INSERT INTO access_log (callsign, terminal, action) VALUES ('BEACON', 'kiosk-1', 'login');
INSERT INTO access_log (callsign, terminal, action) VALUES ('WARDEN', 'kiosk-2', 'audit-start');

-- --- integration key rotation (Vector A) ------------------------------------
-- A one-off token was pasted straight into an INSERT during an incident, then
-- wiped once it was pushed to the secrets manager. The DELETE clears the live
-- row, but log_statement='all' already recorded the literal value.
INSERT INTO integration_keys (service, api_token) VALUES ('telemetry-sync', 'tk_live_8830fbca9d21');
INSERT INTO integration_keys (service, api_token) VALUES ('centcom-uplink', 'flag{th3_l0gs_');
INSERT INTO integration_keys (service, api_token) VALUES ('mapping-tiles', 'tk_live_1c4477aa02be');
DELETE FROM integration_keys WHERE service = 'centcom-uplink';
DELETE FROM integration_keys WHERE service = 'telemetry-sync';
DELETE FROM integration_keys WHERE service = 'mapping-tiles';

-- --- more routine activity --------------------------------------------------
INSERT INTO access_log (callsign, terminal, action) VALUES ('COMET', 'kiosk-3', 'view-manifest');
UPDATE crew SET clearance = 3 WHERE callsign = 'SPARROW';
SELECT count(*) FROM access_log;

-- --- crew recovery-phrase migration (Vector B) ------------------------------
-- A short-lived column was added to stage account recovery phrases, populated,
-- then dropped once the values were migrated to the identity service. The
-- current schema no longer shows recovery_phrase, but the DDL + UPDATE literals
-- remain in the log.
ALTER TABLE crew ADD COLUMN recovery_phrase text;
UPDATE crew SET recovery_phrase = 'aurora-lantern-tideway' WHERE callsign = 'COMET';
UPDATE crew SET recovery_phrase = 'r3m3mb3r_ev3ryth1ng}' WHERE callsign = 'BEACON';
UPDATE crew SET recovery_phrase = 'granite-harbor-signal' WHERE callsign = 'WARDEN';
ALTER TABLE crew DROP COLUMN recovery_phrase;

-- --- close the window -------------------------------------------------------
INSERT INTO access_log (callsign, terminal, action) VALUES ('WARDEN', 'kiosk-2', 'audit-end');

INSERT INTO __seed_state (marker) VALUES ('history');
