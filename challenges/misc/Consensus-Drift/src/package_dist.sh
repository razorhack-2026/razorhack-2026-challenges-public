#!/usr/bin/env bash
# Assemble the competitor handout: dist/consensus-drift.tar.gz
# Run from the challenge root: bash src/package_dist.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # challenge root

STAGE="$(mktemp -d)"
PKG="$STAGE/consensus-drift"
mkdir -p "$PKG/convoy"

cp dist/convoy/node-*.db "$PKG/convoy/"
cp src/ConvoyBridge.sol  "$PKG/ConvoyBridge.sol"
# NOTE: the node DB wire format is intentionally NOT shipped (see src/WIRE_FORMAT.md,
# GM-internal). Reverse-engineering it is part of the challenge.

cat > "$PKG/HANDOUT.txt" <<'TXT'
Consensus-Drift
===============

You have:
  convoy/node-01.db .. node-07.db   the seven convoy nodes' on-disk databases (binary,
                                    undocumented format -- reverse engineering it is
                                    part of the challenge)
  ConvoyBridge.sol                  source of the on-chain bridge you relay to

Your instance (host/ports on the scoreboard) exposes:
  - an Ethereum JSON-RPC endpoint with ConvoyBridge deployed on it
  - a flag dispenser over nc: it prints the bridge address and releases the sealed
    salvage record once the bridge has finalized the manifest.

Goal: get the bridge to finalize the salvage manifest, then read the record from the
dispenser.
TXT

tar --sort=name --mtime='2026-01-01 00:00:00' --owner=0 --group=0 --numeric-owner \
    -czf dist/consensus-drift.tar.gz -C "$STAGE" consensus-drift
rm -rf "$STAGE"
echo "wrote dist/consensus-drift.tar.gz ($(du -h dist/consensus-drift.tar.gz | cut -f1))"
tar -tzf dist/consensus-drift.tar.gz
