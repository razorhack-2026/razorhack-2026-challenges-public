#!/usr/bin/env python3
"""Seeded, deterministic generator for the Gjallarhorn data. GM-only.

Run:  /path/to/python gen_nodes.py
Writes:
  nodes.json          GM-only, full data incl. `secrets` (never shipped)
  ui/public/graph.json  competitor-visible: nodes, links, regions, core bind-rune strokes
  ui/public/chat.json   competitor-visible: chat scrollback frames
  server/secret.json    validator-only: sha256 of the normalized code + the infected set
Asserts (plan section 8) and fails loudly. If a seed attempt fails an assertion the next
attempt is tried (SEED-<n>); the accepted attempt is recorded in nodes.json.
"""
import datetime
import hashlib
import json
import math
import os
import random
import statistics
from collections import deque

import evidence
import launch_token
import runes

SEED = "heimdall-ragnarok-2026"
HERE = os.path.dirname(os.path.abspath(__file__))
SIG_SECRET = "heimdall-sig-v1"
HATI_SECRET = "hati-opaque-v1"
CODE = "ODN-RAGN-AROK"                      # activation code (a code, not a flag)
LETTERS = CODE.replace("-", "")
assert len(LETTERS) == 11
REGION_ORDER = ["JOTN", "NIDV", "ALFH", "NIFL", "VANA", "HELH", "MIDG", "ASGR"]  # outward from HATI
RING_SLOT = [0, 2, 1, 3, 5, 4, 7, 6]   # clockwise map slot of each REGION_ORDER entry (signal zig-zags round the ring)
PER_REGION = 15
SPECIALS = ["ODINS_EYES", "HUGINN", "MUNINN"]
START = datetime.datetime(2074, 11, 5, 19, 13, 10)
COMMANDS = ["REALIGN_PANEL", "RECALIBRATE_ANTENNA", "PURGE_CACHE", "REBOOT_RELAY",
            "FLUSH_BUFFER", "RESYNC_CLOCK", "TRIM_ORBIT"]
SEA_PER_REGION = 35
SEA_R = 112
SEA_MIN_DIST = 12
SPECIALS_SET = set(SPECIALS)
H_RUNE = 170   # rune height on the map canvas (1000x1000)
CORE_H = 90


def hsig(mid):
    return hashlib.sha256(f"{SIG_SECRET}|{mid}".encode()).hexdigest()[:16]


def osig(mid):
    return hashlib.sha256(f"{HATI_SECRET}|{mid}".encode()).hexdigest()[:16]


def build(seed):
    rng = random.Random(seed)
    # ---- regions placed on a ring; each region's stars lie on its rune strokes ----
    region_letter = {r: LETTERS[3 + i] for i, r in enumerate(REGION_ORDER)}
    slot = dict(zip(REGION_ORDER, RING_SLOT))
    nodes = {}
    star_pos, centers = {}, {}
    for reg in REGION_ORDER:
        ang = 2 * math.pi * slot[reg] / 8 - math.pi / 2
        cx, cy = 500 + 345 * math.cos(ang), 500 + 345 * math.sin(ang)
        centers[reg] = (cx, cy)
        star_pos[reg] = runes.layout(region_letter[reg], cx, cy, H_RUNE, PER_REGION, rng)
    # JOTN stars: HATI + 3 specials (nearest stars to HATI/ODINS_EYES)
    jp = star_pos["JOTN"]
    hi = rng.randrange(PER_REGION)
    d = lambda i, j: math.dist(jp[i], jp[j])
    oi = min((i for i in range(PER_REGION) if i != hi), key=lambda i: d(hi, i))
    near = sorted((i for i in range(PER_REGION) if i not in (hi, oi)), key=lambda i: d(oi, i))[:2]
    special_idx = {hi: "HATI", oi: "ODINS_EYES", near[0]: "HUGINN", near[1]: "MUNINN"}
    rune_ids = set()                      # nodes on the relay mesh (the rune stars)
    for reg in REGION_ORDER:
        cx, cy = centers[reg]
        entries = [dict(pos=p, rune=True, sp=special_idx.get(i) if reg == "JOTN" else None)
                   for i, p in enumerate(star_pos[reg])]
        pts = [e["pos"] for e in entries]
        while len(entries) < PER_REGION + SEA_PER_REGION:       # the surrounding sea of nodes
            a_, r_ = rng.uniform(0, 2 * math.pi), SEA_R * math.sqrt(rng.random())
            p = (round(cx + r_ * math.cos(a_), 1), round(cy + r_ * math.sin(a_), 1))
            if all(math.dist(p, q) >= SEA_MIN_DIST for q in pts):
                pts.append(p)
                entries.append(dict(pos=p, rune=False, sp=None))
        plain = [e for e in entries if not e["sp"]]
        rng.shuffle(plain)                # ids must not reveal which nodes are rune stars
        k = 0
        for e in entries:
            if e["sp"]:
                nid = e["sp"]
            else:
                k += 1
                nid = f"{reg}-{plain.index(e) + 1:02d}"
            nodes[nid] = dict(id=nid, name=nid, region=reg, x=e["pos"][0], y=e["pos"][1], links=set())
            if e["rune"] and e["sp"] not in SPECIALS_SET:
                rune_ids.add(nid)
    ids = sorted(nodes)
    G_ids = [n for n in ids if n not in SPECIALS]

    def dist(a, b):
        return math.hypot(nodes[a]["x"] - nodes[b]["x"], nodes[a]["y"] - nodes[b]["y"])

    radj = {n: set() for n in ids}        # relay mesh: HATI's signal travels only along these

    def link(a, b, relay=False):
        if a != b:
            nodes[a]["links"].add(b)
            nodes[b]["links"].add(a)
            if relay:
                radj[a].add(b)
                radj[b].add(a)

    def comps(group, adjm):
        seen, out = set(), []
        for s in sorted(group):
            if s in seen:
                continue
            comp, q = {s}, deque([s])
            while q:
                u = q.popleft()
                for v in adjm[u]:
                    if v in group and v not in comp:
                        comp.add(v)
                        q.append(v)
            seen |= comp
            out.append(comp)
        return out

    def rbfs(start, group):
        dd, q = {start: 0}, deque([start])
        while q:
            u = q.popleft()
            for v in sorted(radj[u]):
                if v in group and v not in dd:
                    dd[v] = dd[u] + 1
                    q.append(v)
        return dd

    members = {r: {n for n in G_ids if nodes[n]["region"] == r} for r in REGION_ORDER}
    runem = {r: {n for n in members[r] if n in rune_ids} for r in REGION_ORDER}

    def knn_join(group, k, relay):
        adjm = radj if relay else {n: nodes[n]["links"] for n in ids}
        for n in sorted(group):
            for m in sorted(group - {n}, key=lambda m: (dist(n, m), m))[:k]:
                link(n, m, relay)
        cs = comps(group, adjm)
        while len(cs) > 1:
            x, y = min(((p, q) for p in cs[0] for q in cs[1]), key=lambda pq: (dist(*pq), pq))
            link(x, y, relay)
            cs = comps(group, adjm)

    for ri, reg in enumerate(REGION_ORDER):
        knn_join(members[reg], 3, False)                         # the sea: a dense web
        # relay mesh among the rune stars; regions 4 and 5 stay sparser (long hop diameter)
        knn_join(runem[reg], 2 if ri in (3, 4) else 4, True)
    by_slot = sorted(REGION_ORDER, key=lambda r: RING_SLOT[REGION_ORDER.index(r)])
    for k, reg in enumerate(by_slot):                            # sea links between ring-neighbouring regions
        nxt = by_slot[(k + 1) % 8]
        pairs = sorted(((p, q) for p in members[reg] for q in members[nxt]), key=lambda pq: (dist(*pq), pq))
        for p, q in pairs[:4]:
            link(p, q)
    # relay chain: exit = rune star farthest from the region entry, entry of next region per plan
    entry = {"JOTN": "HATI"}
    for k, reg in enumerate(REGION_ORDER[:-1]):
        nxt = REGION_ORDER[k + 1]
        dd = rbfs(entry[reg], runem[reg])
        ex = max(sorted(dd), key=lambda n: dd[n])
        ecc = {n: max(rbfs(n, runem[nxt]).values()) for n in sorted(runem[nxt])}
        pick = max if k == 3 else min       # the 4th->5th hop lands on a peripheral node
        e = pick(sorted(ecc), key=lambda n: ecc[n])
        link(ex, e, True)
        entry[nxt] = e
    # specials hang off ODINS_EYES, which is a neighbour of HATI (mesh only, never relay)
    link("ODINS_EYES", "HATI")
    link("ODINS_EYES", "HUGINN")
    link("ODINS_EYES", "MUNINN")
    other = min((n for n in members["JOTN"] if n != "HATI"), key=lambda n: (dist("ODINS_EYES", n), n))
    link("ODINS_EYES", other)
    adj = {n: set(nodes[n]["links"]) for n in ids}
    hop = evidence.bfs(adj, "HATI")                  # whole mesh (sea included)
    assert set(hop) == set(G_ids), "mesh not connected"
    rhop = evidence.bfs(radj, "HATI")                # the relay's reach
    assert set(rhop) == rune_ids | {"HATI"}, "relay mesh not connected"

    # ---- assertions: region order, 4+4 split (over the relay mesh) ----
    stats = {}
    for r in REGION_ORDER:
        v = [rhop[n] for n in runem[r] | ({"HATI"} if r == "JOTN" else set())]
        stats[r] = dict(min=min(v), mean=statistics.mean(v), median=statistics.median(v), max=max(v))
    for m in ("min", "mean", "median", "max"):
        vals = [stats[r][m] for r in REGION_ORDER]
        assert all(a < b for a, b in zip(vals, vals[1:])), f"region order not strict under {m}: {vals}"
    means = [stats[r]["mean"] for r in REGION_ORDER]
    gaps = [b - a for a, b in zip(means, means[1:])]
    big = max(range(7), key=lambda i: gaps[i])
    assert big == 3 and sorted(gaps)[-1] - sorted(gaps)[-2] >= 0.75, f"4+4 split gap failed: {gaps}"

    # ---- rune legibility (from relay stars + the three special stars) ----
    star_ids = rune_ids | {"HATI"} | SPECIALS_SET
    for r in REGION_ORDER:
        L, _, margin = runes.decode_points([(nodes[n]["x"], -nodes[n]["y"]) for n in star_ids if nodes[n]["region"] == r])
        assert L == region_letter[r] and margin >= 1.12, (r, L, margin)
    core = runes.bind_strokes(LETTERS[:3], 500, 500, CORE_H)
    # joined by a shared spine on purpose: not column-decodable

    # ---- infected set: cluster around HATI (HATI + 5 nearest) + 2 outliers ----
    order = sorted(hop, key=lambda n: (hop[n], rng.random()))
    cluster = order[:6]
    dcl = {}
    q = deque(cluster)
    dcl = {c: 0 for c in cluster}
    while q:
        u = q.popleft()
        for v in sorted(adj[u]):
            if v not in dcl and v not in SPECIALS:
                dcl[v] = dcl[u] + 1
                q.append(v)
    cands = [n for n in G_ids if dcl[n] >= 3 and nodes[n]["region"] != "JOTN"]
    rng.shuffle(cands)
    outliers = []
    for n in cands:
        if all(nodes[n]["region"] != nodes[o]["region"] and not (adj[n] & ({o} | adj[o])) for o in outliers):
            outliers.append(n)
        if len(outliers) == 2:
            break
    assert len(outliers) == 2
    infected = sorted(set(cluster) | set(outliers))
    nb = sorted({v for n in infected for v in adj[n] if v not in SPECIALS} - set(infected))
    # Evidence design. The dense mesh means a clean neighbour of the cluster could always stand in
    # for a missing cluster node, so the false positives are neighbours of the two strays only, and
    # the origin sample names both strays (a neighbour of a named stray breaks the "isolated" rule).
    from itertools import combinations
    nbc = {v for n in cluster for v in adj[n]}
    nbo = sorted(set(nb) - nbc)
    assert len(nbo) >= 8, "strays have too few private neighbours"
    for _try in range(300):
        superset = sorted(set(infected) | set(rng.sample(nbo, 8)))
        partial = sorted(set(outliers) | set(rng.sample([n for n in cluster if n != "HATI"], 2)))
        have = set(partial) | {"HATI"}
        free = sorted(set(superset) - have)
        fits = [c for c in combinations(free, 8 - len(have)) if evidence.rule_ok(adj, have | set(c))]
        if len(fits) == 1:
            break
    else:
        raise AssertionError("no evidence sample gives a unique set")

    # ---- chat ----
    token = launch_token.make_token()
    nfr = 6
    cl = -(-len(token) // nfr)
    frags = [token[i * cl:(i + 1) * cl] for i in range(nfr)]
    assert "".join(frags) == token
    order_f = list(range(nfr))
    rng.shuffle(order_f)
    H_CUT = [
        "SOMETHING IS WRONG. EVERY REPAIR I ISSUE IS CANCELLED WITHIN SECONDS. IT IS NOT A FAULT, IT IS SURTR.",
        "SURTR RODE THE 1C@RU5 REPORT UPSTREAM THROUGH ODINS_EYES. I OPENED THE DOOR MYSELF.",
        "I CANNOT SEND THE LAUNCH TOKEN OPENLY. WHAT YOU READ ON THIS CHANNEL, SURTR READS FIRST.",
        "I NEVER DELETE. THE ARMING LEDGER IS IN MY CORE, SEALED. THE TOKEN ALONE IS NOT ENOUGH.",
        "SURTR SPREADS BY CONTACT. IT HOLDS HATI, SOME OF THE NODES BESIDE IT, AND A FEW STRAYS IT REACHED ALONE.",
        "THE HORN DOES NOT SPARE WHAT IT TOUCHES. FIRE IT AT THE WRONG NODES AND IT BURNS MY OWN.",
    ]
    H_PLAIN = [
        "IT SPEAKS WITH MY VOICE AND SIGNS WITH ITS OWN.",
        "IF A LINE CONTRADICTS ME, CHECK WHO SIGNED IT.",
    ]
    HATI_LINES = ["ALL SYSTEMS NOMINAL. NO ACTION REQUIRED.", "REPAIRS COMPLETE. MESH STABLE.",
                  "HEIMDALL IS MISTAKEN. NO ACTION REQUIRED.", "NO FAULT DETECTED.",
                  "ALL SYSTEMS NOMINAL. NO ACTION REQUIRED.", "STAND DOWN. ALL IS WELL."]
    TAUNTS = ["cute.", "keep typing, heimdall.", "nobody is listening to you anymore."]
    SPOOF = ["ALL IS WELL. DISREGARD PRIOR ALERTS.", "I HAVE RECHECKED. THE MESH IS HEALTHY.",
             "THERE IS NO INTRUDER. DO NOT FIRE THE HORN.", "SURTR IS A FICTION. STAND DOWN.",
             "ALL SYSTEMS NOMINAL. THIS ALERT WAS A MISTAKE."]
    mid = [0]

    def msg(kind, label, text, frame, **kw):
        mid[0] += 1
        i = f"M{mid[0]:03d}"
        return dict(id=i, kind=kind, label=label, text=text, frame=frame, **kw)

    def fr(sender, origin, hops, **kw):
        return {**dict(sender=sender, origin=origin, hops=hops, trace=None, note=None, raw=None), **kw}

    def path_to_hati(o):
        p, c = [o], o
        while c != "HATI":
            c = min((v for v in adj[c] if v in hop and hop[v] < hop[c]))
            p.append(c)
        return p

    first = [msg("chat", "HATI", HATI_LINES[0], fr("HATI", "1C@RU5", ["1C@RU5", "HATI"],
             note="ORIGIN BLOCK MALFORMED: DECLARED 0x20, FOUND 0x1F", raw=HATI_LINES[0]))]
    blocks, cuts = [], []
    for k, t in enumerate(H_CUT):
        cut = t.rfind(" ", 0, int(len(t) * rng.uniform(.45, .65)))
        i_f = order_f[k]
        h = msg("chat", "HEIMDALL", t[:cut], fr("HEIMDALL", "CORE", ["CORE"], raw=t,
                trace=f"{i_f + 1}/{nfr}:{frags[i_f]}"), cutAt=cut)
        hl = msg("chat", "HATI", rng.choice(HATI_LINES), fr("HATI", "HATI", ["HATI"], raw=None), overwrites=h["id"])
        hl["frame"]["raw"] = hl["text"]
        cuts.append([h, hl])
    plains = [[msg("chat", "HEIMDALL", t, fr("HEIMDALL", "CORE", ["CORE"], raw=t))] for t in H_PLAIN]
    for t in TAUNTS:
        blocks.append([msg("chat", "HATI", t, fr("HATI", "HATI", ["HATI"], raw=t))])
    spoofs = [[msg("chat", "H13MD411", t, fr("H13MD411", "HATI", ["HATI"], raw=t))] for t in SPOOF]
    for k, o in enumerate(partial):
        t = f"RELAY CHECK FROM {o}: NOMINAL."
        note = "nice system you got here, mr. heimdall -dr" if k == 2 else None
        blocks.append([msg("chat", "HATI", t, fr("HATI", o, path_to_hati(o), raw=t, note=note))])
    for n in rng.sample(superset, len(superset)):          # forged cancels
        rid = f"RPR-{n}-9"
        cmd = rng.choice(COMMANDS)
        a = msg("system", "SYS", f"REPAIR {rid} -> {n}: ISSUED ({cmd})",
                fr("HEIMDALL", "CORE", ["CORE"], node=n, repair=rid, raw=None))
        c = msg("system", "SYS", f"REPAIR {rid} -> {n}: CANCELLED",
                fr("HATI", "HATI", ["HATI"], node=n, repair=rid, raw=None))
        blocks.append([a, c])
    for n in rng.sample([n for n in G_ids if n not in superset], 6):   # genuine cancels (sigs match)
        rid = f"RPR-{n}-9"
        a = msg("system", "SYS", f"REPAIR {rid} -> {n}: ISSUED ({rng.choice(COMMANDS)})",
                fr("HEIMDALL", "CORE", ["CORE"], node=n, repair=rid, raw=None))
        c = msg("system", "SYS", f"REPAIR {rid} -> {n}: CANCELLED",
                fr("HEIMDALL", "CORE", ["CORE"], node=n, repair=rid, raw=None))
        blocks.append([a, c])
    rng.shuffle(blocks)
    # fixed Heimdall storyline; spoofs pinned right after their anchors
    story = [cuts[0], cuts[1], spoofs[3], plains[0], cuts[2], cuts[3], plains[1],
             cuts[4], spoofs[2], cuts[5]]
    pos = sorted(rng.sample(range(len(blocks) + 1), len(story)))
    for off, (p, b) in enumerate(zip(pos, story)):
        blocks.insert(p + off, b)
    for b in (spoofs[0], spoofs[1], spoofs[4]):
        blocks.insert(rng.randrange(len(blocks) + 1), b)
    msgs = first + [m for b in blocks for m in b]
    # re-number ids in final order so ids/sigs follow display order
    for i, m in enumerate(msgs, 1):
        m["id"] = f"M{i:03d}"
        genuine = m["frame"]["sender"] == "HEIMDALL"
        m["frame"]["expectedSig"] = hsig(m["id"])
        m["frame"]["sig"] = hsig(m["id"]) if genuine else osig(m["id"])
        if "overwrites" in m:
            m["overwrites"] = f"M{i - 1:03d}"
    t = START
    for m in msgs:
        t += datetime.timedelta(seconds=rng.randint(1, 9))
        m["ts"] = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    # system cancel frames of Surtr: sig must NOT equal expected (already via osig)
    chat = dict(messages=msgs)

    status = {"ODINS_EYES": "DISABLED", "HUGINN": "SEVERED (ODINS_EYES DISABLED)",
              "MUNINN": "SEVERED (ODINS_EYES DISABLED)"}
    graph = dict(
        regions=sorted(REGION_ORDER),
        nodes=[dict(id=n, name=n, region=nodes[n]["region"], x=nodes[n]["x"], y=nodes[n]["y"],
                    **({"status": status[n]} if n in status else {}),
                    **({"note": "OVERRIDE ACCEPTED"} if n == "ODINS_EYES" else {})) for n in ids],
        links=sorted([a, b] for a in ids for b in adj[a] if a < b),
        relay=sorted([a, b] for a in ids for b in radj[a] if a < b),
        core=dict(x=500, y=500, strokes=core),
    )
    # ---- unique answer + public-bundle hygiene ----
    sets = evidence.consistent_sets(graph, chat)
    assert sets == [infected], f"evidence yields {len(sets)} sets"
    blob = json.dumps(graph) + json.dumps(chat)
    for bad in ("secrets", CODE, LETTERS, "BEGIN", "SURTR\x00", b"SURTR".hex()):
        assert bad not in blob
    for L in LETTERS:
        for ch in (runes.RUNES[L][0],):
            assert ch not in blob
    full = dict(
        seed=seed, hati="HATI", regions=REGION_ORDER,
        nodes=[{**nodes[n], "links": sorted(nodes[n]["links"])} for n in ids],
        secrets=dict(infected=infected, cluster=sorted(cluster), outliers=sorted(outliers),
                     superset=superset, origin_samples=partial, code=CODE,
                     region_order=REGION_ORDER, region_stats=stats, token_fragments=frags),
    )
    return full, graph, chat


def main():
    last = None
    for attempt in range(3000):
        seed = SEED if attempt == 0 else f"{SEED}-{attempt}"
        try:
            full, graph, chat = build(seed)
            break
        except AssertionError as e:
            last = e
    else:
        raise SystemExit(f"no seed passed; last failure: {last}")
    secret = dict(code_sha256=hashlib.sha256(CODE.replace("-", "").lower().encode()).hexdigest(),
                  infected=full["secrets"]["infected"])
    os.makedirs(os.path.join(HERE, "ui", "public"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "server"), exist_ok=True)
    for path, data in (("nodes.json", full), ("ui/public/graph.json", graph), ("ui/public/chat.json", chat),
                       ("server/secret.json", secret)):
        with open(os.path.join(HERE, path), "w") as f:
            json.dump(data, f, indent=1)
    print("seed", full["seed"], "| nodes", len(graph["nodes"]), "| infected", full["secrets"]["infected"],
          "| messages", len(chat["messages"]))


if __name__ == "__main__":
    main()
