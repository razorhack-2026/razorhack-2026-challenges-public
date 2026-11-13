# src/engineering_workstation/config.py - all tunables live here.
import os
import secrets

# Loopback only: the workstation shares vpn-gateway's network namespace (one Fargate
# task; network_mode service:vpn-gateway locally), so it is reachable solely from inside
# the gateway SSH session, which is the pivot.
HOST = "127.0.0.1"
PORT = 5000

# The second credential (recovered from vpn-gateway's /opt/backups/eng-sync.tar.gz).
# MUST match src/vpn_gateway/eng-sync.conf exactly.
ENG_USER = "svc_eng"
ENG_PASS = "EngSync_2087"

# Last Mile's PLC address as seen from vpn-gateway (competitors tunnel to it through the
# gateway). process-plc shares the same network namespace and listens on loopback, so the
# defaults are 127.0.0.1 and its own ports. Override via env only if that changes.
PROCESS_PLC_HOST = os.environ.get("PROCESS_PLC_HOST", "127.0.0.1")
PROCESS_PLC_PORT = os.environ.get("PROCESS_PLC_PORT", "502")
PROCESS_PLC_STATUS_PORT = os.environ.get("PROCESS_PLC_STATUS_PORT", "8000")

# The centrifuge controller's factory-default maintenance unlock code, printed on the
# commissioning sheet in the Documents panel. MUST match DEFAULT_UNLOCK_CODE in
# src/process_plc/config.py exactly.
PLC_UNLOCK_CODE = "4087"

# Flask session secret. Random per container start unless set via env, so a competitor
# can't forge a signed session cookie and skip the credential from the gateway backup.
# The app runs as a single process, so one random key per start is consistent.
SECRET_KEY = os.environ.get("WORKSTATION_SECRET_KEY") or secrets.token_hex(32)

# Flag (operator reference only). The live copy competitors see is rendered on the
# notes panel after login - this value MUST NOT appear in any contestant-facing handout.
FLAG = "flag{the_second_door_was_never_locked}"
