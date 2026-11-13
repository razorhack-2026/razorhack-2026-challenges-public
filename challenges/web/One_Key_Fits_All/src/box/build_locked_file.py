#!/usr/bin/env python3
"""
GM-only build input. Encrypts the real recovery payload (which contains
the flag) with VoidCrypt's static key, producing locked_dashboard.bin —
the only artifact that ends up on the box image (see ./Dockerfile, which
COPYs this file in). The plaintext below never ships anywhere.

The key here MUST be the same value as RECOVERY_KEY in docker-compose.yml
(the one the portal hands back on the paid victim's case page) — that
shared, never-rotated key is the entire vulnerability. If you regenerate
one, regenerate the other to match.

Usage:
    python build_locked_file.py --out locked_dashboard.bin --key <fernet-key>
"""
import argparse

from cryptography.fernet import Fernet

PAYLOAD = b"""RAZERPOWERCO - FIELD OPERATIONS OFFICE
RECOVERY DASHBOARD SNAPSHOT
================================================
Incident: VoidCrypt ransomware deployment, 2026-10-12
Status prior to recovery: ALL SYSTEMS LOCKED

flag{never_reuse_your_recovery_keys}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output path for the locked file")
    ap.add_argument("--key", required=True, help="fernet key, must match docker-compose.yml RECOVERY_KEY")
    args = ap.parse_args()

    fernet = Fernet(args.key.encode())
    token = fernet.encrypt(PAYLOAD)

    with open(args.out, "wb") as fh:
        fh.write(token)

    print(f"Wrote {len(token)} bytes to {args.out}")


if __name__ == "__main__":
    main()
