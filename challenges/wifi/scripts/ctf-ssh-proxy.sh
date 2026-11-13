#!/bin/bash

PID="$1"

if [ -z "$PID" ]; then
    echo "ERROR: CTF container PID was not provided" >&2
    exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: CTF container process $PID is not running" >&2
    exit 1
fi

exec nsenter -t "$PID" -n -- socat STDIO TCP:127.0.0.1:22