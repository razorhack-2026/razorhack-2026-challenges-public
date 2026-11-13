#!/usr/bin/env bash
# Build and start the replay oracle. The flag has one home -- challenge.yml.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLAG="${FLAG:-$(sed -n 's/^[[:space:]]*-[[:space:]]*\(flag{[^}]*}\).*/\1/p' "$ROOT/challenge.yml" | head -1)}"
[ -n "$FLAG" ] || { echo "[-] no flag found in challenge.yml" >&2; exit 1; }
export FLAG
cd "$ROOT"
docker compose up -d --build "$@"
docker compose ps
