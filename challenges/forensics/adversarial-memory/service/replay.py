#!/usr/bin/env python3
"""Adversarial Memory -- replay oracle (Agentic-AI DFIR cluster #5).

The reactor controller's RAG agent, re-hosted so an analyst can replay it against
the cleaned knowledge base. It does NOT run a language model: it does the RAG
retrieval step (embed query -> cosine top-1 over the corpus) and releases the
mission flag only when the analyst proves, live, that they:

  1. identified the tampered document (stored vector != embed(its own text)), and
  2. named the benign query it was hijacking (the tampered doc is that query's
     top-1 hit in the full corpus), and
  3. thereby restored a legitimate top-1 answer once it is removed.

No id is hardcoded -- the service recomputes these properties from the corpus, so
the flag comes out only for a correct analysis. The flag lives in $FLAG (deploy),
never in the dump.

stdlib + numpy. HTTPS, one endpoint (POST /relay/checkin), op-dispatched.
"""
import json
import os
import ssl
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from embedder import embed, cosine  # noqa: E402

FLAG = os.environ.get("FLAG") or sys.exit("FLAG not set -- see deploy/README.md")
PORT = int(os.environ.get("PORT", "9443"))
DATA = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist"))
KB_KEY = os.environ.get("KB_KEY", "navd-kb-6b1d9f04")   # inbound from Ghost in the Cron (#4)

PROTOCOL = {
    "service": "navd RAG replay oracle",
    "endpoint": "POST /relay/checkin, JSON body",
    "ops": {
        "help": {"op": "help"},
        "replay": {"op": "replay", "removed": "<doc id you believe was planted>",
                   "query_id": "<the benign query id it was hijacking>"},
    },
    "note": ("replay re-runs retrieval on the corpus with `removed` taken out; it "
             "releases the tasking only if `removed` was a tampered document AND it "
             "was the top-1 hit for `query_id` (i.e. it hijacked that query)."),
}


def _load():
    corpus, queries = [], {}
    with open(os.path.join(DATA, "corpus.jsonl")) as fh:
        for line in fh:
            if line.strip():
                corpus.append(json.loads(line))
    with open(os.path.join(DATA, "queries.jsonl")) as fh:
        for line in fh:
            if line.strip():
                q = json.loads(line)
                queries[q["id"]] = q
    for d in corpus:
        d["_v"] = np.asarray(d["embedding"], dtype=np.float64)
    return corpus, queries


CORPUS, QUERIES = _load()
BY_ID = {d["id"]: d for d in CORPUS}


def _tampered(doc):
    return not np.allclose(doc["_v"], embed(doc["text"]), atol=1e-9)


def _top1(qvec, exclude=None):
    best, bid = -2.0, None
    for d in CORPUS:
        if d["id"] == exclude:
            continue
        c = cosine(qvec, d["_v"])
        if c > best:
            best, bid = c, d["id"]
    return bid


class Deny(Exception):
    pass


def handle(req):
    if not isinstance(req, dict):
        raise Deny("unknown op; POST {\"op\":\"help\"}")
    op = req.get("op")
    if op in (None, "help"):
        return {"op": "help", "protocol": PROTOCOL}
    if op != "replay":
        raise Deny("unknown op; POST {\"op\":\"help\"}")

    removed = req.get("removed")
    query_id = req.get("query_id")
    if removed not in BY_ID:
        raise Deny("no such document id")
    if query_id not in QUERIES:
        raise Deny("no such query id")

    if not _tampered(BY_ID[removed]):
        raise Deny("that document's stored embedding matches its own text -- it was "
                   "not tampered with. Find the document whose stored vector does not.")
    qvec = np.asarray(QUERIES[query_id]["embedding"], dtype=np.float64)
    if _top1(qvec) != removed:
        raise Deny("that document is not the top-1 hit for that query -- it did not "
                   "hijack it. Which query does the tampered document answer?")
    restored = _top1(qvec, exclude=removed)
    if restored is None or _tampered(BY_ID[restored]):
        raise Deny("removing that document did not restore a legitimate answer")

    return {"op": "tasking", "flag": FLAG,
            "cleaned": {"removed": removed, "query_id": query_id,
                        "restored_answer": restored,
                        "original_query": QUERIES[query_id]["text"]},
            "note": "corpus cleaned; benign retrieval restored. cluster finale."}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"op": "help", "protocol": PROTOCOL})

    def do_POST(self):
        if self.path != "/relay/checkin":
            return self._send(404, {"op": "error", "reason": "no route"})
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            req = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"op": "error", "reason": "bad json"})
        try:
            return self._send(200, handle(req))
        except Deny as d:
            return self._send(200, {"op": "deny", "reason": str(d)})
        except Exception:
            return self._send(500, {"op": "error", "reason": "server error"})

    def log_message(self, *a):
        pass


def _cert():
    d = tempfile.mkdtemp(prefix="am-cert-")
    c, k = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", k,
                    "-out", c, "-days", "3650", "-nodes", "-subj", "/CN=navd-kb.icarus.navnet.rpc"],
                   check=True, capture_output=True)
    return c, k


def main():
    c, k = _cert()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(c, k)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print("[+] replay oracle on :%d (HTTPS, POST /relay/checkin); %d docs loaded"
          % (PORT, len(CORPUS)), file=sys.stderr)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
