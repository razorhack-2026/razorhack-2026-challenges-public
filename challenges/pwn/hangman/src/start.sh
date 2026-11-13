#!/bin/sh
set -eu

PORTS="$PORTS"

echo "Starting listeners on: $PORTS"

for p in $(echo "$PORTS" | tr ',' ' '); do
  echo "Launching listener on $p"
  ( CHAL_PORT="$p" exec socat -d -d \
  TCP-LISTEN:"$p",reuseaddr,fork,keepalive \
  EXEC:"./hangman",pty,rawer,echo=0,igncr,stderr ) &
done

wait
