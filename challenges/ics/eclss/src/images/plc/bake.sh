#!/bin/bash
# bake.sh <program.zip> <modbus_port> <api_port>
#
# Runs once, at image build time, inside the OpenPLC v4.3.1 runtime image. It
# compiles the challenge program into the image and leaves the runtime set to
# run it, so a container (one Fargate task per team) starts with the PLC
# already running in a few seconds instead of re-uploading and compiling.
#
# Both PLCs share one network namespace with the Ignition gateway, and every
# port in it is reachable from the team's Kali box. So the runtime's REST API
# (it can download the running program, whose source holds every flag) is
# moved to 127.0.0.1:<api_port>, and the LAN discovery responder is turned off.
set -euo pipefail

ZIP="$1"
MODBUS_PORT="$2"
API_PORT="$3"
cd /workdir

# 1) REST API on localhost only, on this PLC's own port; no UDP discovery.
sed -i "s/host=\"0.0.0.0\",/host=\"127.0.0.1\",/; s/port=8443,/port=${API_PORT},/" webserver/app.py
sed -i 's/^network_discovery_responder.start()$/pass  # RazorHack: no LAN discovery/' webserver/app.py
grep -q 'host="127.0.0.1",' webserver/app.py
grep -q "port=${API_PORT}," webserver/app.py
grep -q '^pass  # RazorHack: no LAN discovery' webserver/app.py

# 2) Start the runtime and wait for its API.
./start_openplc.sh > /tmp/openplc.log 2>&1 &
API="https://127.0.0.1:${API_PORT}/api"
for i in $(seq 1 90); do
    curl -ksSf "$API/version" > /dev/null 2>&1 && break
    [ "$i" -eq 90 ] && { echo "runtime API never answered"; cat /tmp/openplc.log; exit 1; }
    sleep 2
done

# 3) A throwaway admin (random password, never stored), then upload + compile.
USER=razorhack
PASS="$(head -c 24 /dev/urandom | base64 | tr -d '/+=\n')"
curl -ksS -X POST "$API/create-user" -H "Content-Type: application/json" \
    -d "{\"username\":\"$USER\",\"password\":\"$PASS\",\"role\":\"admin\"}" -o /dev/null
TOKEN=$(curl -ksS -X POST "$API/login" -H "Content-Type: application/json" \
    -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" \
    | tr -d '\n' | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -n "$TOKEN" ] || { echo "login failed"; exit 1; }
curl -ksSf -X POST "$API/upload-file" -H "Authorization: Bearer $TOKEN" -F "file=@$ZIP" -o /dev/null
for i in $(seq 1 300); do
    S=$(curl -ksS "$API/compilation-status" -H "Authorization: Bearer $TOKEN" | tr -d '\n' \
        | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([A-Z_]*\)".*/\1/p')
    [ "$S" = SUCCESS ] && break
    [ "$S" = FAILED ] && { curl -ksS "$API/compilation-status" -H "Authorization: Bearer $TOKEN"; exit 1; }
    [ "$i" -eq 300 ] && { echo "compile timed out (last status: $S)"; exit 1; }
    sleep 2
done
curl -ksSf "$API/start-plc" -H "Authorization: Bearer $TOKEN" -o /dev/null

# 4) Prove it runs: the Modbus slave must be listening on its port.
CONF=core/src/drivers/plugins/python/modbus_slave/modbus_slave.json
grep -q "\"port\": ${MODBUS_PORT}" "$CONF" || { echo "program's Modbus port is not ${MODBUS_PORT}:"; cat "$CONF"; exit 1; }
HEXPORT=$(printf '%04X' "$MODBUS_PORT")
for i in $(seq 1 60); do
    awk 'NR > 1 && $4 == "0A" {print $2}' /proc/net/tcp | grep -q ":${HEXPORT}$" && break
    [ "$i" -eq 60 ] && { echo "Modbus never listened on ${MODBUS_PORT}"; tail -50 /tmp/openplc.log; exit 1; }
    sleep 2
done
echo "[bake] program compiled and running, Modbus on ${MODBUS_PORT}, API on 127.0.0.1:${API_PORT}"

# 5) Stop cleanly (SIGTERM reaches the webserver, which stops plc_main), tidy up.
#    The image has no procps, so find the processes through /proc.
pids() {
    for p in /proc/[0-9]*; do
        tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -Eq "$1" && basename "$p"
    done
    return 0
}
kill -TERM $(pids 'webserver\.app') 2>/dev/null || true
for i in $(seq 1 30); do [ -z "$(pids 'webserver\.app|build/plc_main|build/etherdog')" ] && break; sleep 1; done
kill -KILL $(pids 'webserver\.app|build/plc_main|build/etherdog') 2>/dev/null || true
rm -f /var/run/runtime/*.socket /tmp/openplc.log "$ZIP"
