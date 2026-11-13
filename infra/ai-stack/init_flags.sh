#!/bin/sh
# Writes flags/<challenge>.env (FLAG=...) from each challenge's challenge.yml, so the
# flag the service hands out always matches the one CTFd checks. Never commit flags/.
set -eu
cd "$(dirname "$0")"
mkdir -p flags
for name in loose-lips overprivileged-relay poisoned-telemetry chain-of-command; do
  yml="../../challenges/ai/$name/challenge.yml"
  if [ ! -f "$yml" ]; then echo "skip $name: no challenge.yml yet"; continue; fi
  flag=$(grep -o 'flag{[^}]*}' "$yml" | head -1)
  [ -n "$flag" ] || { echo "no flag in $yml" >&2; exit 1; }
  printf 'FLAG=%s\n' "$flag" > "flags/$name.env"
  echo "wrote flags/$name.env"
done
chmod 600 flags/*.env 2>/dev/null || true
