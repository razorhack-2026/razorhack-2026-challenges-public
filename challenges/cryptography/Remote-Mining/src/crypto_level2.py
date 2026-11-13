#!/usr/bin/env python3
"""
DRILL CONTAINMENT UNIT - hash mining challenge, level 2.

Players must find the nonce that, appended to BLOCK_DATA, produces TARGET_HASH
under SHA-256. Wrong keys lock the console for LOCKOUT_SECONDS.

Uses only stdin/stdout, so it works in a local terminal, under the DCU daemon
on THE-DRILL (exit status 0 = solved), or behind a network wrapper such as:
    socat TCP-LISTEN:1337,reuseaddr,fork EXEC:"python3 -u crypto_level2.py"
"""

import hashlib
import string
import sys
import time

BLOCK_DATA = "DCU-07|SHAFT:K-5|BLOCK:000418|PREV:908cb5|NONCE:"
# Only the hash is stored; the answer never appears in this file.
TARGET_HASH = "c0cf8ef4c7e6abf7152d5f0f4be3a08eed44ac7a8a7add6a9135c1af376c1064"
NONCE_LENGTH = 7
CHARSET = "0123456789abcdef"
FLAG = "flag{H!9h-V@1u3-Emp10y33!}"
# Terminal styling.
RESET = "\033[0m"
BOLD = "\033[1m"
TIME = "\033[38;5;159m"
BANNER_STYLE = "\033[1;30;48;5;229m"  # bold black on pale yellow (229)

LOCKOUT_SECONDS = 15

BANNER = r"""
/////////////////////////////////////////////////////////
//                                                     //
//          D R I L L   C O N T A I N M E N T          //
//                U N I T   D O G - 0 2                //
//                                                     //
/////////////////////////////////////////////////////////
"""


def say(text=""):
    print(text, flush=True)


def sha256_hex(text):
    return hashlib.sha256(text.encode()).hexdigest()


def flush_stdin():
    """Discard anything typed during the lockout (TTY or socket)."""
    try:
        if sys.stdin.isatty():
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        else:
            import os
            import select
            fd = sys.stdin.fileno()
            while select.select([fd], [], [], 0)[0]:
                if not os.read(fd, 4096):
                    break
    except Exception:
        pass


def lockout():
    say(f"[!] CONSOLE LOCKED for {TIME}{LOCKOUT_SECONDS} seconds{RESET}.")
    for remaining in range(LOCKOUT_SECONDS, 0, -1):
        print(f"    unlocking in {TIME}{remaining}{RESET}...", flush=True)
        time.sleep(1)
    flush_stdin()
    say("[*] Console unlocked.\n")


def valid_format(key):
    return len(key) == NONCE_LENGTH and all(c in CHARSET for c in key)


def main():
    say()
    for line in BANNER.strip("\n").splitlines():
        say(f"{BANNER_STYLE}{line}{RESET}")
    say()
    say("Enter the code to help the drill maneuver and mine the KALIUM deposit.")
    say(f"Provide the {NONCE_LENGTH}-character DIS (drill input sequence) to mine the KALIUM:")
    say("    sha256(BLOCK_DATA + DIS) == DEPOSIT_SHAPE")
    say(f"DIS charset: {CHARSET}")
    say(f"Wrong keys lock the console for {TIME}{LOCKOUT_SECONDS} seconds{RESET}.\n")
    say(f"BLOCK_DATA   : {BLOCK_DATA}{'?' * NONCE_LENGTH}")
    say(f"DEPOSIT_SHAPE: {BOLD}{TARGET_HASH}{RESET}\n")

    attempts = 0
    while True:
        try:
            print("ENTER KEY> ", end="", flush=True)
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            say("\n[*] Session terminated.")
            return 1
        if not line:  # EOF / connection closed
            say("\n[*] Session terminated.")
            return 1

        key = line.strip().lower()
        if not valid_format(key):
            say(f"[-] Invalid key format. Need exactly {NONCE_LENGTH} characters from: {CHARSET}\n")
            continue

        attempts += 1
        digest = sha256_hex(BLOCK_DATA + key)
        if digest == TARGET_HASH:
            say("")
            say("[+] CORRECT KEY. Block mined.")
            say(f"[+] DIS '{key}' matches the deposit shape.")
            say(f"[+] Containment released after {attempts} attempt{'s' if attempts != 1 else ''}.")
            say(f"[+] {FLAG}")
            return 0
        say(f"[-] WRONG KEY. '{key}' hashes to {digest[:16]}...")
        try:
            lockout()
        except KeyboardInterrupt:
            say("\n[*] Session terminated.")
            return 1


if __name__ == "__main__":
    sys.exit(main())