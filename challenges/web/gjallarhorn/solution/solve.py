#!/usr/bin/env python3
"""Reference solve. Uses ONLY what a competitor sees (graph.json + chat.json), then asks the live validator.

  python solve.py --url http://localhost:8080            # fetch data from the service, submit
  python solve.py --data ../src/ui/public --url ...       # read data from files
  python solve.py --data ../src/ui/public                  # offline: derive + print, no submit
Needs only the stdlib; reuses the rune templates / evidence helpers in ../src (GM-side).
"""
import argparse
import json
import os
import statistics
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import evidence  # noqa: E402
import runes  # noqa: E402


def load(args, name):
    if args.data:
        return json.load(open(os.path.join(args.data, name)))
    return json.load(urllib.request.urlopen(f"{args.url}/{name}"))


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        return {"http": e.code, **json.loads(e.read() or b"{}")}


def derive_code(graph, head):
    # HATI's relay signal only travels along the `relay` links (the animation lights exactly those)
    radj = {n["id"]: set() for n in graph["nodes"]}
    for a, b in graph["relay"]:
        radj[a].add(b)
        radj[b].add(a)
    hop = evidence.bfs(radj, "HATI")
    stars = set(hop) | evidence.SPECIAL          # lit nodes (+ the three severed stars of JOTN's rune)
    byreg = {}
    for n in graph["nodes"]:
        if n["id"] in stars:
            byreg.setdefault(n["region"], []).append(n)
    letter, stat = {}, {}
    for r, ns in byreg.items():
        L, _, margin = runes.decode_points([(n["x"], -n["y"]) for n in ns])
        assert margin > 1.05, (r, margin)
        letter[r] = L
        v = [hop[n["id"]] for n in ns if n["id"] in hop]
        stat[r] = dict(min=min(v), mean=statistics.mean(v), median=statistics.median(v), max=max(v))
    orders = {m: tuple(sorted(stat, key=lambda r: stat[r][m])) for m in ("min", "mean", "median", "max")}
    assert len(set(orders.values())) == 1, orders           # one answer, whatever metric you pick
    order = orders["mean"]
    means = [stat[r]["mean"] for r in order]
    gaps = [b - a for a, b in zip(means, means[1:])]
    assert max(range(7), key=lambda i: gaps[i]) == 3        # the 4 + 4 split
    body = head + "".join(letter[r] for r in order)
    return f"{body[:3]}-{body[3:7]}-{body[7:]}"


def derive_token(chat):
    fr = {}
    for m in chat["messages"]:
        t = m["frame"].get("trace")
        if t:
            idx, frag = t.split(":", 1)
            i, n = map(int, idx.split("/"))
            fr[i] = frag
    assert sorted(fr) == list(range(1, n + 1))
    return "".join(fr[i] for i in sorted(fr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--data")
    ap.add_argument("--head", help="first 3 code letters (else prompted)")
    a = ap.parse_args()
    assert a.url or a.data
    graph, chat = load(a, "graph.json"), load(a, "chat.json")
    head = (a.head or input("First three code letters (core bind-rune, conjoined): ")).strip().upper()
    assert len(head) == 3, "need 3 letters"
    code, token = derive_code(graph, head), derive_token(chat)
    sets = evidence.consistent_sets(graph, chat)
    assert len(sets) == 1, f"evidence gives {len(sets)} sets"
    print("code ", code)
    print("token", token[:24] + "...", len(token))
    print("set  ", sets[0])
    if not a.url:
        return
    print("check code ", post(f"{a.url}/api/check", {"code": code}))
    print("check token", post(f"{a.url}/api/check", {"token": token}))
    print("purge      ", post(f"{a.url}/api/purge", {"code": code, "token": token, "nodes": sets[0]}))


if __name__ == "__main__":
    main()
