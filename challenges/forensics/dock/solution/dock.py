#!/usr/bin/env python3
"""Organizer check: send a fresh OPEN frame to the dock service."""
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from protocol import BANNER, CMD_OPEN, frame  # noqa: E402

HOST = os.environ.get("DOCK_HOST", "127.0.0.1")
PORT = int(os.environ.get("DOCK_PORT", "4444"))


def main():
    nonce = int.from_bytes(os.urandom(4), "little")
    payload = frame(CMD_OPEN, nonce)
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        banner = sock.recv(len(BANNER))
        sock.sendall(payload)
        reply = sock.recv(256)
    print(banner.decode(), end="")
    print(reply.decode(), end="")
    if b"flag{" not in reply:
        sys.exit("no flag in reply")


if __name__ == "__main__":
    main()
