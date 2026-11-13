#!/bin/sh
# Board A gateway: serve fork-per-connection. Each connection is a fresh rtu_server
# that dials Board B (B_HOST:B_PORT) for its own upstream link -> per-team isolation
# end to end (fresh A process + fresh B plant state per connection).
set -eu
: "${B_HOST:?B_HOST required (Board B internal address)}"
: "${B_PORT:?B_PORT required}"
exec socat TCP-LISTEN:9000,reuseaddr,fork EXEC:/app/rtu_server
