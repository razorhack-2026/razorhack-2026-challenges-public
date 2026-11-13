#!/usr/bin/env python3
"""Exercise Odd Pixel's live API and reference solve using stdlib only."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CHALLENGE = os.path.dirname(HERE)
DESCRIPTION = "CT-7 has flagged an anomaly in a chest scan. Complete the diagnostic before the exposure window closes."


def check_description_sync():
    with open(os.path.join(CHALLENGE, "challenge.yml"), encoding="utf-8") as f:
        metadata = f.read()
    with open(os.path.join(CHALLENGE, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    if DESCRIPTION not in metadata or DESCRIPTION not in readme:
        raise AssertionError("challenge.yml and README description must match")


def expected_flag():
    with open(os.path.join(CHALLENGE, "challenge.yml"), encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if value.startswith("- flag{") and value.endswith("}"):
                return value[2:]
    raise RuntimeError("challenge.yml must contain one static flag")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base, path, body=None):
    data = body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def start_server(port, **settings):
    env = {**os.environ, "PORT": str(port), "QUIET": "1", "FLAG": expected_flag(), **settings}
    server = subprocess.Popen(
        [sys.executable, os.path.join(CHALLENGE, "src", "server.py")],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        if server.poll() is not None:
            raise RuntimeError("server exited before becoming ready")
        try:
            call(base, "/")
            return server, base
        except OSError:
            time.sleep(0.1)
    server.terminate()
    server.wait(timeout=5)
    raise RuntimeError("server did not start")


def stop_server(server):
    server.terminate()
    server.wait(timeout=5)


def main():
    check_description_sync()
    expected = expected_flag()
    server, base = start_server(free_port())
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, "solve.py"), base],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode or expected not in result.stdout:
            raise AssertionError("reference solve did not recover the configured flag")

        status, body = call(base, "/api/challenge")
        challenge = json.loads(body)
        if status != 200 or not challenge.get("image"):
            raise AssertionError("challenge image was not returned")
        page = call(base, "/")[1]
        if b"/static/chest-scan.png" not in page:
            raise AssertionError("chest scan context was not included in the web page")
        image_status, image = call(base, "/static/chest-scan.png")
        if image_status != 200 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError("chest scan context image was not served")
        token = challenge["token"]
        status, body = call(base, "/api/submit", {"token": token, "x": -1, "y": -1})
        if status != 403 or b"Wrong pixel" not in body:
            raise AssertionError("wrong answer was not rejected")
        if b"already used" not in call(base, "/api/submit", {"token": token, "x": -1, "y": -1})[1]:
            raise AssertionError("used token was accepted again")
        if call(base, "/api/submit", b"not json")[0] != 400:
            raise AssertionError("malformed JSON was not rejected")
        if call(base, "/api/submit", b" " * 4097)[0] != 400:
            raise AssertionError("oversized body was not rejected")
        if call(base, "/api/not-found")[0] != 404:
            raise AssertionError("unknown route did not return 404")
    finally:
        stop_server(server)

    server, base = start_server(free_port(), TIME_LIMIT="0.1")
    try:
        token = json.loads(call(base, "/api/challenge")[1])["token"]
        time.sleep(0.2)
        status, _ = call(base, "/api/submit", {"token": token, "x": -1, "y": -1})
        if status != 403:
            raise AssertionError("late answer was not rejected")
    finally:
        stop_server(server)

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
