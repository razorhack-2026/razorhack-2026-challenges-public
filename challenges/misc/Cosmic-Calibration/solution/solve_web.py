#!/usr/bin/env python3
"""
Solve the hosted panel through its API and print the flag.

The starting scramble is fixed (SEED), so its inverse solves any fresh panel.

Usage:  python3 solution/solve_web.py [http://host:8082]    (needs numpy)
"""
import json
import os
import random
import sys
import urllib.request
from http.cookiejar import CookieJar

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from rubik2d import SEED, scramble  # noqa: E402

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8082"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def post(path, body):
    req = urllib.request.Request(base + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(opener.open(req))


post("/api/new", {})
undo = [name + {1: "'", -1: "", 2: "2"}[q]
        for name, q in reversed(scramble(rng=random.Random(SEED)))]
state = post("/api/moves", {"moves": " ".join(undo)})
if not state["solved"]:
    sys.exit("not solved")
print(state["flag"])
