#!/bin/sh
# Overburden entrypoint: materialize the flag from env (never baked into the
# image), then serve the RTU fork-per-connection. Each connection = fresh
# process reading /app/flag.txt, so teams never share mutable state.
set -eu
: "${FLAG:?FLAG env var required — see deploy/README.md}"
printf '%s\n' "$FLAG" > /app/flag.txt
exec socat TCP-LISTEN:"${PORT:-9000}",reuseaddr,fork EXEC:/app/rtu_server
