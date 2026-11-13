#!/usr/bin/env bash
# Produce dist/intercept.pcap: bring up the agent mesh, capture ONLY its data-plane
# bridge while the driver fires the session population, then tear down. A real
# capture of real containers -- only the scenario is scripted.
#
# Linux + Docker (compose v2) + dumpcap. No sudo: dumpcap runs via the 'wireshark'
# group (sudo usermod -aG wireshark "$USER"; log in again).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"            # src/
ROOT="$(cd "$HERE/.." && pwd)"                    # challenge dir
DIST="$ROOT/dist"; mkdir -p "$DIST"
PCAP="$DIST/intercept.pcap"

# the flag has one home -- challenge.yml -- unless FLAG is set explicitly
FLAG="${FLAG:-$(sed -n 's/^[[:space:]]*-[[:space:]]*\(flag{[^}]*}\).*/\1/p' "$ROOT/challenge.yml" | head -1)}"
[ -n "$FLAG" ] || { echo "[-] no flag found in challenge.yml" >&2; exit 1; }
export FLAG

cd "$HERE"
CAP=""
cleanup() { [ -n "$CAP" ] && kill -INT "$CAP" 2>/dev/null || true; docker compose down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker build -q -t tct-mesh:latest . >/dev/null
docker compose up -d --quiet-pull 2>/dev/null
sleep 4                                           # let the subsystems bind

NETID="$(docker network ls --filter name=tct-mesh_mesh --format '{{.ID}}')"
IFACE="br-${NETID:0:12}"
dumpcap -q -P -i "$IFACE" -f 'tcp port 80' -w "$PCAP" &   # -P: classic pcap, not pcapng
CAP=$!
sleep 2                                           # let dumpcap come up

docker compose run --rm -T driver                 # prints the mined/discarded tally
sleep 2                                           # flush the last exchanges
kill -INT "$CAP"; wait "$CAP" || true; CAP=""
docker compose down -v >/dev/null 2>&1
echo "[+] $PCAP ($(wc -c < "$PCAP" | tr -d ' ') bytes)"
