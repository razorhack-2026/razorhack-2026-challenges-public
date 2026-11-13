#!/usr/bin/env bash
# Produce dist/session.pcap + dist/sslkeys.log by running generate.py under a
# loopback packet capture -- a real dumpcap of genuine TLS, not synthesized packets.
#
# Needs dumpcap (Wireshark), openssl, and a Python with `cryptography` (uv is used
# if present; otherwise set PYTHON=/path/to/python). No sudo:
#   Linux -- dumpcap via the 'wireshark' group (sudo usermod -aG wireshark "$USER")
#   macOS -- the 'access_bpf' group the Wireshark installer sets up
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"            # src/
ROOT="$(cd "$HERE/.." && pwd)"                    # challenge dir
DIST="$ROOT/dist"; mkdir -p "$DIST"
PORT="${PORT:-8443}"
PCAP="$DIST/session.pcap"
KEYLOG="$DIST/sslkeys.log"

# the flag has one home -- challenge.yml -- unless FLAG is set explicitly
FLAG="${FLAG:-$(sed -n 's/^[[:space:]]*-[[:space:]]*\(flag{[^}]*}\).*/\1/p' "$ROOT/challenge.yml" | head -1)}"
[ -n "$FLAG" ] || { echo "[-] no flag found in challenge.yml" >&2; exit 1; }
export FLAG KEYLOG_PATH="$KEYLOG" PORT

if [ -n "${PYTHON:-}" ]; then PY=("$PYTHON")
elif command -v uv >/dev/null; then PY=(uv run --quiet --with cryptography python)
else PY=(python3); fi

: > "$KEYLOG"
# capture loopback traffic on our port for a bounded window (harness ~3s)
CAPTURE="dumpcap -q -f 'tcp port $PORT' -a duration:12 -w '$PCAP'"
case "$(uname -s)" in
  Darwin) sh -c "$CAPTURE -i lo0" & ;;
  *)      sg wireshark -c "$CAPTURE -i lo" & ;;
esac
CAP=$!
sleep 1.5                                         # let dumpcap come up
"${PY[@]}" "$HERE/generate.py" 2> >(sed -E 's/flag\{[^}]*\}/flag{...}/g' >&2)   # keep the flag off the terminal
wait "$CAP"                                       # dumpcap stops at the duration cap
echo "[+] $PCAP ($(wc -c < "$PCAP" | tr -d ' ') bytes); $KEYLOG ($(grep -c SECRET "$KEYLOG") secret lines)"
