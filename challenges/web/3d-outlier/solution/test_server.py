#!/usr/bin/env python3
"""Exercise Deep Tissue's CT API, expiry checks, and reference solve."""
import ast
import json
import os
import re
import runpy
import socket
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
CHALLENGE = os.path.dirname(HERE)


def check_description_sync():
    with open(os.path.join(CHALLENGE, "challenge.yml"), encoding="utf-8") as f:
        metadata = f.read()
    with open(os.path.join(CHALLENGE, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    description = re.search(r"^description: \|\n((?: +[^\n]*\n)+)", metadata, re.MULTILINE)
    player_text = readme.split("## Description\n", 1)[1].split("\n## Connection", 1)[0].strip()
    if not description or textwrap.dedent(description[1]).strip() != player_text:
        raise AssertionError("challenge.yml and README description must match")


def expected_flag():
    with open(os.path.join(CHALLENGE, "challenge.yml"), encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if value.startswith("- flag{") and value.endswith("}"):
                return value[2:]
    raise RuntimeError("challenge.yml must contain one static flag")


def check_starting_layer(flag):
    with patch.dict(os.environ, {"FLAG": flag, "SIZE": "512", "TOLERANCE": "2"}):
        server = runpy.run_path(os.path.join(CHALLENGE, "src", "server.py"))
    for seed in range(64):
        volume = server["Volume"](seed)
        starting_z = server["SIZE"] // 2 + 0.5
        if abs(volume.lesion[2] - starting_z) <= volume.r + server["TOLERANCE"]:
            raise AssertionError("lesion overlaps the starting layer or its click tolerance")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base, path, body=None):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(base + path, data, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
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
    for _ in range(100):
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
    check_starting_layer(expected)
    server, base = start_server(free_port())
    try:
        page = call(base, "/")[1]
        if b"/static/brain-scan.png" not in page or b"BRAIN SCAN" not in page:
            raise AssertionError("brain scan context was not included in the web page")
        image_status, image = call(base, "/static/brain-scan.png")
        if image_status != 200 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError("brain scan context image was not served")
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, "solve.py"), base],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode or ast.literal_eval(result.stdout.splitlines()[-1]).get("flag") != expected:
            raise AssertionError("reference solve did not recover the configured flag")

        token = json.loads(call(base, "/api/challenge")[1])["token"]
        if call(base, f"/api/slice?token={token}&z=10")[0] != 200:
            raise AssertionError("slice fetch failed")
        status, body = call(base, "/api/submit", {"token": token, "x": 0, "y": 0, "z": 0})
        if status != 403 or b"Wrong spot" not in body:
            raise AssertionError("wrong spot was accepted")
        if b"already used" not in call(base, "/api/submit", {"token": token, "x": 0, "y": 0, "z": 0})[1]:
            raise AssertionError("used token was accepted again")
        if call(base, "/api/slice?token=invalid&z=10")[0] != 403:
            raise AssertionError("invalid token served a slice")
        if call(base, "/api/submit", b"not json")[0] != 400:
            raise AssertionError("malformed JSON was not rejected")
        if call(base, "/api/submit", b" " * 4097)[0] != 400:
            raise AssertionError("oversized body was not rejected")
    finally:
        stop_server(server)

    server, base = start_server(free_port(), TIME_LIMIT="1")
    try:
        token = json.loads(call(base, "/api/challenge")[1])["token"]
        time.sleep(1.2)
        if call(base, f"/api/slice?token={token}&z=10")[0] != 403:
            raise AssertionError("slice remained available after expiry")
        if b"window closed" not in call(base, "/api/submit", {"token": token, "x": 0, "y": 0, "z": 0})[1]:
            raise AssertionError("late answer was not rejected")
    finally:
        stop_server(server)

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
