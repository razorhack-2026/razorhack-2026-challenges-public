#!/usr/bin/env bash
# Consensus-Drift instance entrypoint: boot a private anvil node, deploy ConvoyBridge
# from the public deploy params, then serve the flag dispenser. The FLAG is materialized
# from the environment at runtime -- it is never baked into the image and never on-chain.
set -euo pipefail

: "${FLAG:?FLAG env var required (inject at runtime, e.g. -e FLAG=flag{...})}"
POW_BITS="${POW_BITS:-24}"
RPC_URL="http://127.0.0.1:8545"
export RPC_URL

echo "[entrypoint] starting anvil..."
anvil --host 0.0.0.0 --port 8545 --silent &
ANVIL_PID=$!

echo "[entrypoint] waiting for RPC..."
for i in $(seq 1 60); do
  if cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1; then break; fi
  sleep 0.5
  if ! kill -0 "$ANVIL_PID" 2>/dev/null; then echo "anvil died"; exit 1; fi
done

echo "[entrypoint] deploying ConvoyBridge (POW_BITS=$POW_BITS)..."
POW_BITS="$POW_BITS" /opt/venv/bin/python /app/deploy.py \
  --params /app/deploy_params.json --out /app/bridge_address.txt

export BRIDGE_ADDR_FILE=/app/bridge_address.txt
echo "[entrypoint] starting flag dispenser on :9000"
exec /opt/venv/bin/python /app/dispenser.py
