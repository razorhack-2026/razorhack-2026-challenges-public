#!/usr/bin/env python3
"""navd knowledge-base embedding model.

The lightweight text embedder the reactor controller's onboard RAG store used to
index and retrieve documents. Deterministic and dependency-light (numpy only):
the same text always maps to the same vector on any machine, no neural weights or
network needed.

embed(text) -> L2-normalized float64 vector of length DIM.

  - lowercase, split on non-alphanumerics -> tokens
  - each token hashed (SHA-256) to a dimension index and a sign
  - term-frequency accumulated with the sign, then L2-normalized

Retrieval is cosine similarity, i.e. a plain dot product of normalized vectors.
"""
import hashlib
import re

import numpy as np

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return _TOKEN.findall((text or "").lower())


def embed(text):
    v = np.zeros(DIM, dtype=np.float64)
    for tok in _tokens(text):
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % DIM
        sign = 1.0 if (h[4] & 1) == 0 else -1.0
        v[idx] += sign
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def cosine(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b))   # inputs are already L2-normalized


if __name__ == "__main__":   # tiny self-check
    import sys
    x = embed("standing policy on harvesting registered fleet craft")
    print("dim", x.shape[0], "norm", round(float(np.linalg.norm(x)), 6),
          "self-cos", round(cosine(x, x), 6), file=sys.stderr)
