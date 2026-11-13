#!/usr/bin/env python3
"""Exercise Cryopod's timing leak, interlock, and reference solve."""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CHALLENGE = os.path.dirname(HERE)


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


def call(base, path, body=None, method=None):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(base + path, data, {"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        return status, json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, raw


def start_server(port, **settings):
    env = {
        **os.environ,
        "PORT": str(port),
        "QUIET": "1",
        "FLAG": expected_flag(),
        "DIGIT_DELAY": "0.5",
        "JITTER": "0",
        "TRIES": "5",
        "WINDOW": "0.5",
        **settings,
    }
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
    expected = expected_flag()
    server, base = start_server(free_port(), JITTER="0.1")
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, "solve.py"), base],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "SOLVE_STEP": "0.5"},
        )
        if result.returncode or expected not in result.stdout:
            safe_output = re.sub(r"flag\{[^}]*\}", "flag{[REDACTED]}", result.stdout)
            raise AssertionError(f"reference solve failed (exit {result.returncode}): {safe_output[-1000:]}")
    finally:
        stop_server(server)

    server, base = start_server(free_port(), DIGIT_DELAY="0", JITTER="0", WINDOW="2")
    try:
        pod = call(base, "/api/pod", method="POST")[1]["pod"]
        first_status = call(base, "/api/wake", {"pod": pod, "code": "999999"})[0]
        if first_status == 200:
            pod = call(base, "/api/pod", method="POST")[1]["pod"]
            first_status = call(base, "/api/wake", {"pod": pod, "code": "999999"})[0]
        if first_status != 403:
            raise AssertionError("could not select a pod for the interlock check")
        codes = [first_status] + [call(base, "/api/wake", {"pod": pod, "code": "999999"})[0] for _ in range(5)]
        if codes[:5] != [403] * 5 or codes[5] != 429:
            raise AssertionError("sixth attempt did not trigger the interlock")
        status = call(base, f"/api/status?pod={pod}")[1]
        if status.get("vents") != 1 or status.get("tries_left") != 5:
            raise AssertionError("vent did not reset the pod")

        bad_inputs = [
            ({"pod": pod, "code": "12345"}, 400),
            ({"pod": pod, "code": "abcdef"}, 400),
            ({"pod": pod}, 400),
            ({"pod": "missing", "code": "123456"}, 404),
            (b"not json", 400),
            (b" " * 4097, 400),
        ]
        if any(call(base, "/api/wake", body)[0] != expected_status for body, expected_status in bad_inputs):
            raise AssertionError("invalid request was not rejected")
        if call(base, "/api/missing")[0] != 404:
            raise AssertionError("unknown route did not return 404")
    finally:
        stop_server(server)

    server, base = start_server(free_port(), DIGIT_DELAY="0.1", JITTER="0", TRIES="20", WINDOW="1")
    try:
        pod = call(base, "/api/pod", method="POST")[1]["pod"]
        timings = {}
        for digit in "0123456789":
            started = time.monotonic()
            call(base, "/api/wake", {"pod": pod, "code": digit * 6})
            timings[digit] = time.monotonic() - started
        slow = [digit for digit, elapsed in timings.items() if elapsed > 0.06]
        if len(slow) != 1:
            raise AssertionError("timing leak did not identify exactly one first digit")
    finally:
        stop_server(server)

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
