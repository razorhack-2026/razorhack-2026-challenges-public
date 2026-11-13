"""Public-evidence reasoning shared by the generator (unique-answer assert) and solution/solve.py.

Works ONLY from what a competitor sees: graph.json + chat.json.
"""
from collections import deque
from itertools import combinations

SPECIAL = {"ODINS_EYES", "HUGINN", "MUNINN"}


def adjacency(graph):
    adj = {n["id"]: set() for n in graph["nodes"]}
    for a, b in graph["links"]:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def bfs(adj, start, skip=SPECIAL):
    d, q = {start: 0}, deque([start])
    while q:
        u = q.popleft()
        for v in sorted(adj[u]):
            if v not in d and v not in skip:
                d[v] = d[u] + 1
                q.append(v)
    return d


def evidence(chat, node_ids):
    """-> (superset, partial): nodes with a forged cancel signature, and HATI-message origins."""
    sup, part = set(), set()
    for m in chat["messages"]:
        f = m["frame"]
        if m["kind"] == "system" and f.get("node") and f["sig"] != f["expectedSig"]:
            sup.add(f["node"])
        if f.get("origin") and f["origin"] in node_ids and f["sender"] in ("HATI", "H13MD411"):
            part.add(f["origin"])
    return sup, part


def rule_ok(adj, X, hati="HATI", cluster=6):
    """Surtr = a connected cluster holding HATI (size 6) + 2 strays with no neighbour inside the set."""
    if hati not in X:
        return False
    comp, q = {hati}, deque([hati])
    while q:
        u = q.popleft()
        for v in adj[u] & X:
            if v not in comp:
                comp.add(v)
                q.append(v)
    rest = X - comp
    return len(comp) == cluster and all(not (adj[r] & X) for r in rest)


def consistent_sets(graph, chat, size=8):
    adj = adjacency(graph)
    sup, part = evidence(chat, set(adj))
    free = sorted(sup - part)
    out = []
    for extra in combinations(free, size - len(part)):
        X = part | set(extra)
        if rule_ok(adj, X):
            out.append(sorted(X))
    return out
