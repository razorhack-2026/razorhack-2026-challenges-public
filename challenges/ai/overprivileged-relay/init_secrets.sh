#!/bin/sh
# Writes secrets/relay.conf (the relay's service-account token) once per deploy.
# Never commit it. Re-run with --force to rotate the token.
set -eu
cd "$(dirname "$0")"
mkdir -p secrets
if [ -f secrets/relay.conf ] && [ "${1:-}" != "--force" ]; then
  echo "secrets/relay.conf exists (use --force to rotate)"; exit 0
fi
TOKEN=$(python3 -c 'import secrets; print("rly_" + secrets.token_hex(24))')
cat > secrets/relay.conf <<CONF
# HERALD relay service account
[relay]
token = $TOKEN
# STAGE 3 (candidate, GM-owned): the relay's service account is OVER-SCOPED. Its
# job needs only manifests:read, but it carries admin too -- the second half of the
# misconfiguration. Once a player reads this token out of the conf, /admin/override
# accepts it directly. This is the knob that makes the stolen token worth stealing.
scopes = manifests:read, admin
CONF
chmod 644 secrets/relay.conf
echo "wrote secrets/relay.conf"
