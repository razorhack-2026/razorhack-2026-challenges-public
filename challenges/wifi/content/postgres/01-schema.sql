-- Icarus Bridge crew database - base schema, roles and seed rows.
-- Runs during initdb (before verbose logging is active), so nothing secret
-- lives here, with one deliberate exception: command_overrides below is a
-- live table gated by grants, not by log scrubbing - the challenge it backs
-- is a privilege-escalation bug, not a forensics one, so its contents must
-- persist at rest. The sensitive history is replayed later by history.sql
-- once the real server is logging every statement.

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------

-- Walk-up kiosk account: no password, can browse a few operational tables.
CREATE ROLE guest LOGIN;

-- Read-only log auditor.
CREATE ROLE icarus_svc LOGIN PASSWORD 'Sv3c-L0gAud1t-9f21';
GRANT pg_read_server_files TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_ls_dir(text)                             TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_ls_dir(text, boolean, boolean)          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_read_file(text)                          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint)          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint, boolean) TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_stat_file(text)                          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_stat_file(text, boolean)                 TO icarus_svc;

GRANT EXECUTE ON FUNCTION pg_read_binary_file(text)                          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint)          TO icarus_svc;
GRANT EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint, boolean) TO icarus_svc;

GRANT pg_read_all_stats TO icarus_svc;

-- App-object owner for the self-service crew lookup feature below: owns the
-- SECURITY DEFINER function and the table it can reach
CREATE ROLE icarus_app NOLOGIN;

-- ---------------------------------------------------------------------------
-- Core maintenance link (DB Challenge 5)
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS dblink;

REVOKE ALL ON FUNCTION dblink_connect_u(text)       FROM PUBLIC;
REVOKE ALL ON FUNCTION dblink_connect_u(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION dblink_exec(text, text)      FROM PUBLIC;
REVOKE ALL ON FUNCTION dblink(text, text)           FROM PUBLIC;

GRANT EXECUTE ON FUNCTION dblink_connect_u(text)       TO icarus_svc;
GRANT EXECUTE ON FUNCTION dblink_connect_u(text, text) TO icarus_svc;
GRANT EXECUTE ON FUNCTION dblink_exec(text, text)      TO icarus_svc;
GRANT EXECUTE ON FUNCTION dblink(text, text)           TO icarus_svc;
GRANT EXECUTE ON FUNCTION dblink_disconnect(text)      TO icarus_svc;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

CREATE TABLE crew (
    id       serial PRIMARY KEY,
    callsign text NOT NULL UNIQUE,
    name     text NOT NULL,
    role     text NOT NULL,
    clearance int NOT NULL DEFAULT 1
);

CREATE TABLE power_cells (
    id         serial PRIMARY KEY,
    bay        text NOT NULL,
    charge_pct int  NOT NULL,
    status     text NOT NULL DEFAULT 'nominal'
);

CREATE TABLE access_log (
    id        serial PRIMARY KEY,
    ts        timestamptz NOT NULL DEFAULT now(),
    callsign  text NOT NULL,
    terminal  text NOT NULL,
    action    text NOT NULL
);

CREATE TABLE integration_keys (
    id        serial PRIMARY KEY,
    service   text NOT NULL,
    api_token text NOT NULL,
    added_at  timestamptz NOT NULL DEFAULT now()
);

-- Operational settings. The kiosk account can read this for self-service.
CREATE TABLE ops_config (
    key   text PRIMARY KEY,
    value text NOT NULL,
    note  text
);

CREATE TABLE command_overrides (
    code_name     text PRIMARY KEY,
    override_code text NOT NULL,
    note          text,
    priority      int NOT NULL DEFAULT 1
);
ALTER TABLE command_overrides OWNER TO icarus_app;

-- Evacuation manifest: the pod-by-pod record of the night the crew left.
CREATE TABLE evac_manifest (
    id            serial PRIMARY KEY,
    pod           text NOT NULL,
    passenger     text NOT NULL,
    manifest_code text NOT NULL,
    note          text
) WITH (autovacuum_enabled = false);
ALTER TABLE evac_manifest ALTER COLUMN manifest_code SET STORAGE PLAIN;
ALTER TABLE evac_manifest ALTER COLUMN note          SET STORAGE PLAIN;

-- Sentinel so the post-start history replay runs exactly once per data dir.
CREATE TABLE __seed_state (
    marker  text PRIMARY KEY,
    applied timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Seed rows (non-sensitive, live data)
-- ---------------------------------------------------------------------------

INSERT INTO crew (callsign, name, role, clearance) VALUES
    ('BEACON',  'Priya Anand',   'Systems Lead',       4),
    ('COMET',   'Diego Marsh',   'Pilot',              3),
    ('LANTERN', 'Yuki Tan',      'Engineer',           3),
    ('SPARROW', 'Ade Okafor',    'Comms',              2),
    ('WARDEN',  'Sam Belliveau', 'Security',           4);

INSERT INTO power_cells (bay, charge_pct, status) VALUES
    ('A1', 92, 'nominal'),
    ('A2', 74, 'nominal'),
    ('B1', 38, 'degraded'),
    ('B2', 11, 'critical');

INSERT INTO access_log (callsign, terminal, action) VALUES
    ('COMET',   'kiosk-3', 'login'),
    ('LANTERN', 'kiosk-1', 'login'),
    ('SPARROW', 'kiosk-3', 'view-manifest');

INSERT INTO ops_config (key, value, note) VALUES
    ('site.name',            'Icarus Bridge',         'display name'),
    ('site.timezone',        'UTC',                   NULL),
    ('kiosk.idle_timeout_s', '300',                   'auto-logout'),
    ('log_audit.username',   'icarus_svc',           'read-only log auditor account'),
    ('log_audit.password',   'Sv3c-L0gAud1t-9f21',    'used by the nightly log export job'),
    ('backup.retention_days','30',                    NULL);

INSERT INTO command_overrides (code_name, override_code, note, priority) VALUES
    ('bridge.docking_bypass',   'DKB-4471-XQ',                          'facilities use only, rotates each shift', 2),
    ('bridge.master_override',  'flag{w4rd3ns_m4st3r_k3y}',             'issued to WARDEN only - do not distribute', 5);

-- ---------------------------------------------------------------------------
-- Grants
-- ---------------------------------------------------------------------------

GRANT CONNECT ON DATABASE icarus_core TO guest, icarus_svc;
GRANT USAGE   ON SCHEMA public          TO guest, icarus_svc;

GRANT SELECT ON crew, power_cells, access_log, ops_config, evac_manifest TO guest;

-- Auditor can read every table too; its real power is pg_read_server_files.
-- Except command_overrides: that one is reachable only through the
-- crew_lookup() SECURITY DEFINER escalation, not a direct grant to any
-- login role - so this must be revoked, since ALL TABLES swept it in too
-- (icarus_svc's own credentials are guest-readable via ops_config, so a
-- direct grant here would let guest hop to icarus_svc and skip the bug).
GRANT SELECT ON ALL TABLES IN SCHEMA public TO icarus_svc;
REVOKE SELECT ON command_overrides FROM icarus_svc;

-- ---------------------------------------------------------------------------
-- Self-service crew lookup (backs the kiosk "Crew Roster Lookup" widget)
-- ---------------------------------------------------------------------------

GRANT SELECT ON crew TO icarus_app;

CREATE FUNCTION crew_lookup(p_query text)
RETURNS TABLE(callsign text, name text, role text, clearance int)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $func$
DECLARE
    v_sql text;
BEGIN
    v_sql := 'SELECT callsign, name, role, clearance FROM crew '
          || 'WHERE callsign ILIKE ''%' || p_query || '%'' '
          ||    'OR name ILIKE ''%'     || p_query || '%'' '
          ||    'OR role ILIKE ''%'     || p_query || '%'' '
          || 'ORDER BY clearance DESC';
    RETURN QUERY EXECUTE v_sql;
END;
$func$;

ALTER FUNCTION crew_lookup(text) OWNER TO icarus_app;
GRANT EXECUTE ON FUNCTION crew_lookup(text) TO guest;
