"""Smoke-test DOCK's captured-nonce rejection and cross-connection nonce behavior."""
import os
import socket
import sys
import threading
import time
from pathlib import Path

os.environ["DOCK_FLAG"] = "test_token"
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import app
import protocol


def request(port: int, nonce: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=1) as conn:
        stream = conn.makefile("rb")
        if stream.readline() != protocol.BANNER:
            raise AssertionError("unexpected service banner")
        conn.sendall(protocol.frame(protocol.CMD_OPEN, nonce))
        return stream.readline()


def request_when_ready(port: int, nonce: int) -> bytes:
    deadline = time.monotonic() + 5
    while True:
        try:
            return request(port, nonce)
        except OSError:
            if time.monotonic() >= deadline:
                raise AssertionError("DOCK service did not accept a connection")
            time.sleep(0.05)


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    app.HOST = "127.0.0.1"
    app.PORT = port
    app.FLAG = "test_token"
    threading.Thread(target=app.main, daemon=True).start()

    if request_when_ready(port, protocol.CAPTURED_NONCE) != b"REPLAY_REJECT\n":
        raise AssertionError("captured nonce must be rejected")

    expected = b"OK|test_token\n"
    for _ in range(2):
        if request_when_ready(port, 0x5678) != expected:
            raise AssertionError("the same fresh nonce should work on separate connections")

    print("PASS: captured nonce rejected; fresh nonce reusable across connections")


if __name__ == "__main__":
    main()
