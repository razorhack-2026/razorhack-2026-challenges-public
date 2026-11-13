#!/usr/bin/env bash
# Build the THRUST artifact. Requires gcc.
set -e
cd "$(dirname "$0")"
mkdir -p ../dist
gcc -no-pie -O0 -o ../dist/thruster_ctl thruster_ctl.c
echo "built dist/thruster_ctl"
