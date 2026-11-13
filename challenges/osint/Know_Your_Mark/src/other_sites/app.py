"""One lightweight service shared by the other Sherlock targets."""
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        self.do_HEAD()
        self.wfile.write(b"Not found\n")


def ports(spec: str) -> list[int]:
    """The ports to listen on, from "8100-8123" or "8080,8100-8101"."""
    out = []
    for part in spec.split(","):
        lo, _, hi = part.strip().partition("-")
        out.extend(range(int(lo), int(hi or lo) + 1))
    return out


if __name__ == "__main__":
    # OTHER_SITE_PORTS: compose maps the 24 published ports onto this one 8080. A Fargate
    # copy can't remap ports, so there it listens on 8100-8123 itself (Razorhack-Infra).
    servers = [ThreadingHTTPServer(("0.0.0.0", p), Handler) for p in ports(os.environ.get("OTHER_SITE_PORTS", "8080"))]
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    servers[0].serve_forever()
