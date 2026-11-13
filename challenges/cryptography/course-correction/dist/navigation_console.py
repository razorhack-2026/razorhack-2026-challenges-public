#!/usr/bin/env python3
"""Offline emergency navigation console. Run with Python 3."""

import hashlib
import hmac
import sys


EXPECTED_OVERRIDE_SHA256 = "072f70a203434a74b8b453c445bf0174e5c0189b3c16a977c4546b28615f6eac"


def main() -> int:
    print(
        "RAZERPOWERCO EMERGENCY NAVIGATION CONSOLE\n"
        "WARNING: Current flight plan intersects a star.\n"
        "Local command authority locked.\n"
    )

    if len(EXPECTED_OVERRIDE_SHA256) != 64 or any(
        char not in "0123456789abcdef" for char in EXPECTED_OVERRIDE_SHA256
    ):
        print(
            "Console setup incomplete: configure a lowercase SHA-256 digest.",
            file=sys.stderr,
        )
        return 2

    while True:
        try:
            supplied_override = input("Emergency override: ")
        except (EOFError, KeyboardInterrupt):
            print("\nSession closed.")
            return 1

        digest = hashlib.sha256(supplied_override.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(digest, EXPECTED_OVERRIDE_SHA256):
            print("OVERRIDE REJECTED\n")
            continue

        print(
            "\nOVERRIDE ACCEPTED\n"
            "Open navigation_log.zip with the override key as its password\n"
            "to read the navigation recovery log."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
