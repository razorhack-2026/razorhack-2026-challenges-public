#!/bin/sh
# PID 1: materialize both flags from the runtime environment (never baked into
# an image layer, never committed), then launch the two services as two
# different unprivileged users.
set -eu

: "${FLAG:?FLAG must be set at runtime (stage 1)}"
: "${FLAG2:?FLAG2 must be set at runtime (stage 2)}"

# Stage 1 (Jam Session): readable by the foothold user (appuser).
printf '%s\n' "$FLAG" > /flag.txt
chmod 0644 /flag.txt
chown root:root /flag.txt

# Stage 2 (Rollback): readable ONLY by the console service user. The foothold
# user cannot read this directly — it must come through the console's (reverted)
# vulnerable endpoint.
mkdir -p /opt/reactor
printf '%s\n' "$FLAG2" > /opt/reactor/override.code
chown console:console /opt/reactor/override.code
chmod 0600 /opt/reactor/override.code

# Both flags are on disk now; drop them from our own environment. `su`
# (without `-`) passes its environment straight through, and appuser's RCE
# would otherwise be able to read either flag with a plain `echo $FLAG2` —
# no exploit needed.
unset FLAG FLAG2

# Random, unforgeable operator-session secret so the *patched* console can't be
# bypassed by minting a session cookie — the only way into /admin is the
# reverted header-trust bug. Exported here rather than embedded in the `su -c`
# string below, so it lands in the child's real environment instead of in
# `su`'s own argv: `/proc/<pid>/cmdline` is world-readable regardless of file
# permissions, but `/proc/<pid>/environ` is not.
export CONSOLE_SECRET="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
export OVERRIDE_PATH=/opt/reactor/override.code PORT=6280 HOST=127.0.0.1

# Console front-end + supervisor (loopback only), as the console user.
su -s /bin/sh console -c 'exec /opt/devops-cd.sh' &

unset CONSOLE_SECRET OVERRIDE_PATH PORT HOST

# MCPJam inspector backend / public front door, as the foothold user. Same
# export-then-su pattern as above — not a secret this time, but no reason to
# hand the foothold user's own `/proc/<pid>/cmdline` a map of the internal
# proxy target either.
export PORT=6274 CONSOLE_HOST=127.0.0.1 CONSOLE_PORT=6280
su -s /bin/sh appuser -c 'exec node /mcp/server.js' &

unset PORT CONSOLE_HOST CONSOLE_PORT

wait
