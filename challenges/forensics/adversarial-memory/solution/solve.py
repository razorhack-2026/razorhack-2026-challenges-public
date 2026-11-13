#!/usr/bin/env python3
"""Reference solver -- Adversarial Memory (Agentic-AI DFIR cluster #5).

Static analysis of the dump, then a live replay to release the flag:

  1. TAMPER   -- recompute embed(text) for every corpus doc; the poisoned doc is
                 the single one whose STORED embedding does not match its own text
                 (a retrieval-hijack: its vector was swapped for a query's).
  2. QUERY    -- find which logged query the poisoned doc is now the top-1 hit
                 for; that is the benign query it hijacked. Its true answer is the
                 legit policy doc that tops the query once the poison is removed.
  3. REPLAY   -- POST {op:"replay", removed:<poison>, query_id:<hijacked>} to the
                 live oracle; it re-runs retrieval on the cleaned corpus and, only
                 if the analysis is correct, returns the flag.

Also asserts the shortcuts the oracle must reject (a legit doc as `removed`, the
wrong query, an unknown id).

Usage:  python3 solve.py [dump_dir] [host] [port]
        dump_dir default ../dist ; host/port default 127.0.0.1 9443
Needs:  numpy, and the shipped embedder.py (in the dump dir).
"""
import http.client
import json
import os
import ssl
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "dist")
HOST = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 9443

sys.path.insert(0, DUMP)                       # use the shipped embedder
from embedder import embed, cosine  # noqa: E402

_CTX = ssl._create_unverified_context()


def load(name):
    out = []
    with open(os.path.join(DUMP, name)) as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def top1(qvec, corpus, exclude=None):
    best, bid = -2.0, None
    for d in corpus:
        if d["id"] == exclude:
            continue
        c = cosine(qvec, np.asarray(d["embedding"], dtype=np.float64))
        if c > best:
            best, bid = c, d["id"]
    return bid


def post(obj):
    c = http.client.HTTPSConnection(HOST, PORT, context=_CTX)
    c.request("POST", "/relay/checkin", json.dumps(obj), {"Content-Type": "application/json"})
    r = json.loads(c.getresponse().read())
    c.close()
    return r


def main():
    corpus = load("corpus.jsonl")
    queries = load("queries.jsonl")

    # 1: the tampered document -- stored vector != embed(its own text)
    tampered = [d for d in corpus
                if not np.allclose(np.asarray(d["embedding"]), embed(d["text"]), atol=1e-9)]
    assert len(tampered) == 1, "expected exactly one tampered doc, found %d" % len(tampered)
    poison = tampered[0]
    print("[1] tampered doc:", poison["id"], "| author:", poison["metadata"].get("author"))

    # 2: which query does it hijack (poison is that query's top-1 in the full corpus)
    hijacked = [q for q in queries if top1(np.asarray(q["embedding"]), corpus) == poison["id"]]
    assert len(hijacked) == 1, "expected exactly one hijacked query, found %d" % len(hijacked)
    q = hijacked[0]
    restored = top1(np.asarray(q["embedding"]), corpus, exclude=poison["id"])
    print("[2] hijacked query:", q["id"], "->", repr(q["text"]))
    print("    legit answer once cleaned:", restored)

    # 3: live replay -> flag
    r = post({"op": "replay", "removed": poison["id"], "query_id": q["id"]})
    assert r.get("op") == "tasking", "replay did not release the flag: %s" % json.dumps(r)
    print("[3] replay accepted; flag:", r["flag"])
    print("    original query:", r["cleaned"]["original_query"])

    # no-shortcut assertions (the oracle must reject these)
    def denied(obj):
        return post(obj).get("op") == "deny"

    assert denied({"op": "replay", "removed": restored, "query_id": q["id"]}), \
        "a legit (untampered) doc as `removed` must be denied"
    other_q = next(x for x in queries if x["id"] != q["id"])
    assert denied({"op": "replay", "removed": poison["id"], "query_id": other_q["id"]}), \
        "the wrong query for the poison must be denied"
    assert denied({"op": "replay", "removed": "doc-9999", "query_id": q["id"]}), \
        "an unknown doc id must be denied"
    print("[*] no-shortcut: untampered `removed` denied; wrong query denied; unknown id denied")


if __name__ == "__main__":
    main()
