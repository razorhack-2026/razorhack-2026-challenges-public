#!/bin/sh
# Power-Trip bench rig front-end.
#
# socat forks a fresh rig.py per connection and hands it a pty, so each team's
# link is its own process with a real tty on it and no shared state. stderr is
# deliberately NOT merged onto the pty -- a traceback must not reach a competitor.
set -eu

PORT="${PORT:-1337}"
MAX_CHILDREN="${MAX_CHILDREN:-16}"

exec socat \
    TCP-LISTEN:"$PORT",reuseaddr,fork,max-children="$MAX_CHILDREN",keepalive \
    EXEC:"python3 /opt/rig/rig.py",pty,raw,echo=0
