"""Shadow Price — reference solver (intended path, both parts).

Standalone: imports nothing from src/ and hardcodes no answer. The only baked-in
knowledge is the mission spec from the brief (primary-system floors).

  1. Browse the PMC-7 address space over OPC UA and rebuild the LP.
  2. Part I: compare model floors with the mission spec, fix the flipped sense,
     solve, ApplyDispatch  -> flag I.
  3. Part II: rank the binding floors by cost (shadow price x floor), drop the
     most expensive one, re-solve, ApplyDispatch -> flag II.

    uv run --with asyncua --with scipy python solve.py [opc.tcp://host:4840/pmc7/]
"""
import asyncio
import sys

import numpy as np
from asyncua import Client
from scipy.optimize import linprog

URL = sys.argv[1] if len(sys.argv) > 1 else "opc.tcp://localhost:4840/pmc7/"

# From the mission spec in the brief: minimum safe draw for the primary systems.
SPEC_FLOORS = {"life_support": 18.0, "thrusters": 10.0, "shields": 8.0, "comms": 3.0, "payload_stasis": 9.0}


async def child(node, name):
    for c in await node.get_children():
        if (await c.read_browse_name()).Name == name:
            return c
    raise KeyError(name)


async def read_model(client):
    pmc = await child(client.nodes.objects, "PMC7")
    reactor = await (await child(await child(pmc, "Reactor"), "RatedOutput_MW")).read_value()
    segs, loops = {}, {}
    for s in await (await child(pmc, "BusSegments")).get_children():
        segs[(await s.read_browse_name()).Name] = await (await child(s, "Capacity_MW")).read_value()
    for l in await (await child(pmc, "CoolantLoops")).get_children():
        loops[(await l.read_browse_name()).Name] = await (await child(l, "Capacity_MWth")).read_value()
    order = await (await child(pmc, "LoadOrder")).read_value()
    loads_node = await child(pmc, "Loads")
    loads = {}
    for k in order:
        n = await child(loads_node, k)
        loads[k] = {p: await (await child(n, p)).read_value()
                    for p in ("BusSegment", "CoolantLoop", "CoolantPerMW", "DispatchWeight",
                              "Floor_MW", "FloorSense", "Cap_MW")}
    current = {k: await (await child(await child(pmc, "CurrentDispatch"), k)).read_value() for k in order}
    method = await child(pmc, "ApplyDispatch")
    return pmc, method, reactor, segs, loops, order, loads, current


def build_and_solve(order, loads, reactor, segs, loops, floors, senses):
    n = len(order)
    w = np.array([loads[k]["DispatchWeight"] for k in order])
    rows, names = [], []
    def row(name, a, b):
        rows.append((np.array(a, float), b)); names.append(name)
    row("reactor", [1.0] * n, reactor)
    for s, cap in segs.items():
        row(f"seg_{s}", [1.0 if loads[k]["BusSegment"] == s else 0 for k in order], cap)
    for l, cap in loops.items():
        row(f"loop_{l}", [loads[k]["CoolantPerMW"] if loads[k]["CoolantLoop"] == l else 0 for k in order], cap)
    for i, k in enumerate(order):
        if floors[k] > 0:
            e = np.zeros(n); e[i] = 1
            if senses[k] == "LE":
                row(f"floor_{k}", e, floors[k])
            else:
                row(f"floor_{k}", -e, -floors[k])
        e = np.zeros(n); e[i] = 1
        row(f"cap_{k}", e, loads[k]["Cap_MW"])
    A = np.array([r[0] for r in rows]); b = np.array([r[1] for r in rows])
    res = linprog(-w, A_ub=A, b_ub=b, bounds=[(0, None)] * n, method="highs")
    assert res.status == 0, res.message
    return res.x, dict(zip(names, -res.ineqlin.marginals)), float(w @ res.x)


async def apply(pmc, method, x, label):
    report, eff = await pmc.call_method(method, [float(v) for v in x])
    print(f"\n===== ApplyDispatch: {label} (efficiency {eff:.2f} %)\n{report}")
    return report


async def main():
    async with Client(url=URL) as client:
        pmc, method, reactor, segs, loops, order, loads, current = await read_model(client)
        await apply(pmc, method, [current[k] for k in order], "controller's CurrentDispatch")

        # ---- Part I: diff the primary floors against the mission spec
        floors = {k: loads[k]["Floor_MW"] for k in order}
        senses = {k: loads[k]["FloorSense"] for k in order}
        for k, spec in SPEC_FLOORS.items():
            if senses[k] != "GE" or abs(floors[k] - spec) > 1e-9:
                print(f"\n[part I] {k}: model says {senses[k]} {floors[k]}, spec says >= {spec} -> fixing")
                senses[k], floors[k] = "GE", spec
        x1, duals, z1 = build_and_solve(order, loads, reactor, segs, loops, floors, senses)
        await apply(pmc, method, x1, "sign-fixed model optimum")

        # ---- Part II: which binding floor costs the most? (shadow price x floor)
        cost = {k: duals[f"floor_{k}"] * floors[k] for k in order
                if k not in SPEC_FLOORS and f"floor_{k}" in duals}
        ranked = sorted(cost.items(), key=lambda kv: -kv[1])
        print("\n[part II] aux floor cost (shadow price x floor):")
        for k, c in ranked[:5]:
            print(f"   {k:12s} {c:8.3f}   (shadow price {duals[f'floor_{k}']:.3f} x {floors[k]} MW)")
        suspect = ranked[0][0]
        print(f"[part II] dropping the floor on {suspect}")
        floors[suspect] = 0.0
        x2, _, z2 = build_and_solve(order, loads, reactor, segs, loops, floors, senses)
        await apply(pmc, method, x2, f"floor on {suspect} dropped")


if __name__ == "__main__":
    asyncio.run(main())
