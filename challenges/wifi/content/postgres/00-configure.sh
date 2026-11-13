#!/bin/bash
# Runs during initdb (docker-entrypoint-initdb.d). At this point PGDATA has been
# initialised and a temporary server is running for the *.sql seed scripts, but
# our logging settings below only take effect once the real server starts. That
# is deliberate: the sensitive history in history.sql is replayed AFTER the real
# server is up (see postgres_startup.sh), so every statement lands in the
# collected log file.
set -e

echo "[+] Applying Icarus Bridge logging + auth configuration"

# --- Verbose statement logging into a single, stable log file ---
cat >>"$PGDATA/postgresql.conf" <<'CONF'

# --- Icarus Bridge audit logging ---
listen_addresses = '*'
logging_collector = on
log_destination = 'stderr'
log_directory = 'log'
log_filename = 'postgresql.log'
log_rotation_age = 0
log_rotation_size = 0
log_truncate_on_rotation = off
log_file_mode = 0640
log_statement = 'all'
log_min_duration_statement = -1
log_line_prefix = '%m [%p] %q%u@%d '
CONF

# --- Host-based auth: guest kiosk (trust), core admin blocked off-box ---
install -m 0600 -o postgres -g postgres \
    /etc/postgresql/pg_hba.conf "$PGDATA/pg_hba.conf"

echo "[+] Configuration applied"
