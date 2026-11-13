#!/usr/bin/env bash
# Coremelt deploy helper. Builds the matiec base image (eng-ws is FROM it),
# then builds and starts the two-host stack.
set -euo pipefail
cd "$(dirname "$0")"

echo "[*] building coremelt-matiec base image (matiec IEC->C compiler)..."
docker build -t coremelt-matiec -f src/matiec/Dockerfile.matiec src/matiec

echo "[*] building + starting the Coremelt stack..."
docker compose up -d --build

echo "[*] up. player-facing service: http://<host>:3000"
docker compose ps
