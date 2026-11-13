#!/bin/bash

set -e

echo "[+] Waiting for wlan0..."

while ! ip link show wlan0 >/dev/null 2>&1; do
    sleep 0.2
done

echo "[+] wlan0 detected"

ip link set wlan0 up

echo "[+] Starting wpa_supplicant"

wpa_supplicant \
    -B \
    -i wlan0 \
    -c /etc/wpa_supplicant/client-bridged.conf

echo "[+] Waiting for Wi-Fi association..."

for i in {1..30}; do
    if iw dev wlan0 link | grep -q "Connected"; then
        echo "[+] Associated with Wi-Fi AP"
        break
    fi

    sleep 1
done

if ! iw dev wlan0 link | grep -q "Connected"; then
    echo "[-] Failed to associate with Wi-Fi AP"
    iw dev wlan0 link
    exit 1
fi

echo "[+] Starting DHCP client"

dhclient wlan0

echo "[+] Network configuration:"
ip addr show wlan0
ip route

echo "[+] Starting PostgreSQL"

# Replay the sensitive operator history AFTER the real server is up and logging.
# We connect over TCP loopback on purpose: the temporary server the entrypoint
# runs during initdb listens on the unix socket only, so a 127.0.0.1 connection
# can only succeed against the final, fully-logging server. pg_hba grants
# postgres trust from 127.0.0.1 (and rejects it from everywhere else).
(
    until pg_isready -q -h 127.0.0.1 -U postgres >/dev/null 2>&1; do
        sleep 0.5
    done
    sleep 1

    # -----------------------------------------------------------------------
    # Lock down the server's own setup files. icarus_svc is in
    # pg_read_server_files, so without this it could pg_ls_dir / pg_read_file
    # them - and 01-schema.sql carries a flag (command_overrides) plus the
    # icarus_svc password at rest, while 00-configure.sh and this startup script
    # would hand out the challenge design. initdb has already run by now (the
    # server is up), so the initdb hooks are no longer needed and are removed
    # outright (also hides their names from pg_ls_dir). This startup script must
    # stay root-executable for a container restart, so it becomes 0500 root
    # (the postgres-uid backend gets EPERM; root can still exec it). The seed
    # SQL files are already 0400 root from the image build.
    #
    # NOTE: /usr/local/bin/docker-entrypoint.sh is deliberately left readable -
    # the stock postgres entrypoint re-exec's ITSELF via `gosu postgres`, so the
    # postgres uid must be able to read/exec it or the container won't start. It
    # holds no secret.
    rm -f /docker-entrypoint-initdb.d/00-configure.sh \
          /docker-entrypoint-initdb.d/01-schema.sql
    chown root:root /usr/local/bin/postgres_startup.sh 2>/dev/null || true
    chmod 0500 /usr/local/bin/postgres_startup.sh 2>/dev/null || true

    already_applied=$(psql -h 127.0.0.1 -U postgres -d icarus_core -tA \
        -c "SELECT 1 FROM __seed_state WHERE marker = 'history'" 2>/dev/null)

    if [ "$already_applied" != "1" ]; then
        echo "[+] (seed) replaying operator history into the server log"
        psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d icarus_core \
            -f /usr/local/bin/history.sql
    else
        echo "[+] (seed) operator history already applied; skipping"
    fi

    # -----------------------------------------------------------------------
    # DB Challenge 4 (heap recovery): the "broken transaction" + heap seed.
    #
    # We first open long-lived holder sessions that BEGIN a REPEATABLE READ
    # transaction and then sit idle-in-transaction forever. Their registered
    # snapshot pins the xmin horizon below the DELETE that heap.sql performs,
    # which keeps the deleted tuple classified RECENTLY_DEAD so neither VACUUM
    # nor opportunistic HOT pruning can reclaim it. This IS the story: the MH-2
    # manifest-hygiene purge committed its DELETE, then the worker running it
    # stalled with an old snapshot still held open.
    #
    # Two invariants that are easy to break later:
    #   * The holders MUST connect to icarus_core. ComputeXidHorizons only folds
    #     a backend's xmin into the (non-catalog) horizon for its OWN database;
    #     a holder on another DB protects nothing.
    #   * The holder warm-up must NOT read evac_manifest - a seqscan of that page
    #     is exactly what would prune the dead tuple. We snapshot with
    #     pg_current_snapshot() instead.
    # A few redundant holders make a single dropped connection non-fatal.
    echo "[+] (seed) opening holder transaction(s) to pin the heap tuples"
    for _h in 1 2 3; do
        {
            printf "SET idle_in_transaction_session_timeout = 0;\n"
            printf "SET statement_timeout = 0;\n"
            printf "BEGIN ISOLATION LEVEL REPEATABLE READ;\n"
            printf "SELECT pg_current_snapshot();\n"
            printf "SELECT 'MH-2 manifest hygiene - purge worker stalled mid-directive';\n"
            sleep infinity
        } | psql -q -f - \
            "host=127.0.0.1 user=postgres dbname=icarus_core application_name=manifest_purge_worker" \
            >/dev/null 2>&1 &
    done

    # Wait until at least one holder has actually registered its snapshot
    # (backend_xmin is the held horizon), so the DELETE happens *after* it.
    for _i in $(seq 1 60); do
        _n=$(psql -h 127.0.0.1 -U postgres -d icarus_core -tA -c \
            "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'manifest_purge_worker' AND backend_xmin IS NOT NULL" 2>/dev/null)
        [ "${_n:-0}" -ge 1 ] 2>/dev/null && { echo "[+] (seed) ${_n} holder snapshot(s) registered"; break; }
        sleep 0.5
    done

    # Content-based guard (self-heals a stale-marker restart): (re)seed unless the
    # non-flag sentinel is already present in the heap file. We probe the sentinel,
    # never 'flag{', so the probe statement can't write flag material anywhere.
    heap_present=$(psql -h 127.0.0.1 -U postgres -d icarus_core -tA -c \
        "SET log_statement='none'; SELECT position('EVAC-DELTA-7' in encode(pg_read_binary_file(pg_relation_filepath('evac_manifest')), 'escape')) > 0" 2>/dev/null | tail -n1)

    if [ "$heap_present" != "t" ]; then
        echo "[+] (seed) seeding + purging evac_manifest (log-silenced, heap-only)"
        psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d icarus_core \
            -f /usr/local/bin/heap.sql >/dev/null
    else
        echo "[+] (seed) evac_manifest heap artifact already present; skipping"
    fi

    # Self-check to container stdout (NOT the PG log). Probes the sentinel only.
    heap_ok=$(psql -h 127.0.0.1 -U postgres -d icarus_core -tA -c \
        "SET log_statement='none'; SELECT position('EVAC-DELTA-7' in encode(pg_read_binary_file(pg_relation_filepath('evac_manifest')), 'escape')) > 0" 2>/dev/null | tail -n1)
    if [ "$heap_ok" = "t" ]; then
        echo "[+] (seed) evac_manifest heap recovery artifact present on disk"
    else
        echo "[-] (seed) WARNING: evac_manifest heap artifact NOT on disk - DB Challenge 4 may be unsolvable"
    fi
) &

exec /usr/local/bin/docker-entrypoint.sh postgres