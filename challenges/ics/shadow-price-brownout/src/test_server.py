"""Shadow Price — end-to-end checks against a running PMC-7 server (GM-only).

Checks the protections the design depends on: fixed timestamps, read-only model,
anonymous/NoSecurity only, believable identity, no flag text in the address
space, stateless ApplyDispatch, input rejection, probe resistance, and the
no-LP / wrong-fix shortcuts. Exits non-zero on any failure.

    uv run --with asyncua --with scipy python test_server.py [opc.tcp://host:4840/pmc7/]
"""
import asyncio
import re
import sys
from datetime import datetime, timezone

import numpy as np
from asyncua import Client, ua

from model import IDX, NAMES, SPEC_FLOORS, build, served_floors, sign_fixed_rows, solve, true_rows

URL = sys.argv[1] if len(sys.argv) > 1 else "opc.tcp://localhost:4840/pmc7/"
MODEL_TS = datetime(2074, 2, 11, 4, 12, tzinfo=timezone.utc)
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


async def walk(node, out):
    for c in await node.get_children():
        cls = await c.read_node_class()
        if cls == ua.NodeClass.Variable:
            out.append(c)
        if cls in (ua.NodeClass.Object, ua.NodeClass.Variable):
            await walk(c, out)
    return out


def alarms(report):
    return sorted(re.findall(r"^\s+(\S+)\s+[\d.]+ MW\s+ALARM", report, re.M))


def awarded(report):
    return ("I" if "Emergency dispatch accepted" in report else "") + \
           ("II" if "optimal dispatch confirmed" in report else "")


async def main():
    async with Client(url=URL) as client:
        # ---- endpoint security + identity
        eps = await client.get_endpoints()
        policies = {e.SecurityPolicyUri.rsplit("#", 1)[-1] for e in eps}
        tokens = {t.TokenType for e in eps for t in e.UserIdentityTokens}
        check("endpoints: NoSecurity only", policies == {"None"}, str(policies))
        check("endpoints: anonymous identity only", tokens == {ua.UserTokenType.Anonymous}, str(tokens))
        bi = client.get_node(ua.ObjectIds.Server_ServerStatus_BuildInfo)
        manu = await (await bi.get_child("0:ManufacturerName")).read_value()
        prod = await (await bi.get_child("0:ProductName")).read_value()
        check("identity: BuildInfo is populated, not library defaults",
              manu == "Orrin-Hale Power Systems" and "PMC-7" in prod, f"{manu} / {prod}")
        ns = await client.get_node(ua.ObjectIds.Server_NamespaceArray).read_value()
        srv = await client.get_node(ua.ObjectIds.Server_ServerArray).read_value()
        check("identity: no freeopcua default URI in NamespaceArray/ServerArray",
              not any("freeopcua" in u for u in ns + srv), f"{ns} {srv}")

        pmc = await client.nodes.objects.get_child("2:PMC7")
        variables = await walk(pmc, [])
        dvs = [await v.read_data_value() for v in variables]
        check("address space: model variables found", len(variables) >= 17 * 8, f"{len(variables)} vars")

        # ---- timestamps + access level
        src_ts = {dv.SourceTimestamp for dv in dvs}
        srv_ts = {dv.ServerTimestamp for dv in dvs}
        check("timestamps: every model value has the one fixed SourceTimestamp",
              src_ts == {MODEL_TS.replace(tzinfo=None)} or src_ts == {MODEL_TS}, str(src_ts))
        check("timestamps: every model value has the one fixed ServerTimestamp",
              srv_ts == {MODEL_TS.replace(tzinfo=None)} or srv_ts == {MODEL_TS}, str(srv_ts))
        levels = set()
        for v in variables:
            levels.add((await v.read_attribute(ua.AttributeIds.AccessLevel)).Value.Value)
        check("access: every model variable has the same AccessLevel (read-only)",
              levels == {ua.AccessLevel.CurrentRead.mask}, str(levels))
        target = await pmc.get_child(["2:Loads", "2:aux_bus_7", "2:Floor_MW"])
        try:
            await target.write_value(0.0)
            wrote = True
        except ua.UaStatusCodeError as e:
            wrote = False; err = type(e).__name__
        check("access: anonymous write to a model node is refused", not wrote, "" if wrote else err)

        # ---- no flag text anywhere in the address space
        strings = [str(dv.Value.Value) for dv in dvs if dv.Value is not None]
        check("leak: no 'flag{' in any address-space value", not any("flag{" in s for s in strings))

        method = await pmc.get_child("2:ApplyDispatch")
        async def call(x):
            report, eff = await pmc.call_method(method, [float(v) for v in x])
            return report, eff

        # ---- statelessness: values unchanged after calls, same input -> same output
        St = solve(true_rows())
        r1, _ = await call(St["x"])
        r2, _ = await call(St["x"])
        after = [await v.read_data_value() for v in variables]
        check("stateless: address space identical after ApplyDispatch calls",
              [(a.Value, a.SourceTimestamp) for a in after] == [(d.Value, d.SourceTimestamp) for d in dvs])
        check("stateless: identical calls give identical reports", r1 == r2)
        check("flags: true optimum awards I and II", awarded(r1) == "III", awarded(r1))
        rr, _ = await call(np.round(St["x"], 2))
        check("flags: true optimum rounded to 2 dp still awards II", "II" in awarded(rr), awarded(rr))

        # ---- input rejection (server must stay up)
        for label, bad in (("short", [1.0] * 5), ("long", [1.0] * 20), ("nan", [float("nan")] * len(NAMES)),
                           ("inf", [float("inf")] + [1.0] * (len(NAMES) - 1)),
                           ("-inf", [float("-inf")] + [1.0] * (len(NAMES) - 1)),
                           ("negative", [-1.0] + [1.0] * (len(NAMES) - 1))):
            rep, _ = await call(bad)
            check(f"input: {label} allocation rejected cleanly", rep.startswith("REJECTED"), rep[:60])

        # ---- controller's own dispatch: only life support alarms, no flag
        cur = await pmc.get_child("2:CurrentDispatch")
        xc = [await (await cur.get_child(f"2:{k}")).read_value() for k in NAMES]
        rep, _ = await call(xc)
        check("current dispatch: only life_support alarms, no flag",
              alarms(rep) == ["life_support"] and awarded(rep) == "", f"{alarms(rep)} {awarded(rep)}")

        # ---- probe resistance: zero one floored aux bus at a time
        f2 = served_floors()
        base = np.array([f2[k] for k in NAMES]); base[IDX["life_support"]] = SPEC_FLOORS["life_support"]
        shapes = {}
        for k in NAMES:
            if not k.startswith("aux") or f2[k] <= 0:
                continue
            xp = base.copy(); xp[IDX[k]] = 0.0
            rep, _ = await call(xp)
            shapes[k] = (alarms(rep), awarded(rep))
        check("probe: zeroing any floored aux bus alarms exactly that bus, and never awards a flag",
              all(a == [k] and f == "" for k, (a, f) in shapes.items()), str(shapes))
        xz = base.copy()
        for k in NAMES:
            if k.startswith("aux"):
                xz[IDX[k]] = 0.0
        rep, _ = await call(xz)
        check("probe: zeroing all aux buses alarms every floored bus incl. aux_bus_7",
              "aux_bus_7" in alarms(rep) and len(alarms(rep)) == 10, str(alarms(rep)))

        # ---- shortcuts
        rep, _ = await call(base)
        check("shortcut: all-floors dispatch (no LP) awards nothing", awarded(rep) == "", awarded(rep))
        check("feedback: safe hand-tuned dispatch says 'safe but below the model's optimum'",
              "safe but below the model's optimum" in rep and alarms(rep) == [])
        fx = dict(f2); fx["aux_bus_7"] = 0.0
        Sx = solve(build(fx, floor_sense={"life_support": "LE"}))
        rep, _ = await call(Sx["x"])
        check("shortcut: fixing aux_bus_7 without the sign flip awards nothing", awarded(rep) == "", awarded(rep))
        S1 = solve(sign_fixed_rows())
        rep, _ = await call(S1["x"])
        check("flags: sign-fixed optimum awards I only", awarded(rep) == "I", awarded(rep))
        check("feedback: no 'below optimum' line once flag I is earned", "below the model's optimum" not in rep)
        rep, _ = await call(xc)
        check("feedback: no 'below optimum' line while an alarm is showing", "below the model's optimum" not in rep)
        lmc = await (await pmc.get_child(["2:Info", "2:LastModelChange"])).read_value()
        check("backstory: Info/LastModelChange says anonymous write, names no load",
              "anonymous" in lmc and not any(k in lmc for k in NAMES), lmc)
        wrong = {}
        for k in NAMES:
            if not k.startswith("aux") or k == "aux_bus_7" or f2[k] <= 0:
                continue
            fk = dict(f2); fk[k] = 0.0
            rep, _ = await call(solve(build(fk))["x"])
            wrong[k] = awarded(rep)
        check("brute force: dropping any legit aux floor never awards II",
              all("II" not in v for v in wrong.values()), str(wrong))

    # ---- dist/pmc7.py: the player helper works and gives nothing away
    import os
    dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist")
    sys.path.insert(0, dist)
    import pmc7
    hp = await pmc7.connect(URL)
    hm = await pmc7.model(hp)
    check("helper: model() returns all 17 loads with 8 properties each",
          len(hm["loads"]) == 17 and all(len(v) == 8 for v in hm["loads"].values()))
    hr, _ = await pmc7.apply(hp, hm["current_dispatch"])
    check("helper: apply(dict) replays CurrentDispatch -> life_support alarm", alarms(hr) == ["life_support"])
    try:
        await pmc7.apply(hp, {k: 0.0 for k in list(hm["current_dispatch"])[:-1]})
        raised = False
    except ValueError:
        raised = True
    check("helper: apply() refuses a dict that doesn't cover every load", raised)
    try:
        await pmc7.apply(hp, [1.0] * 5)
        raised = False
    except ValueError:
        raised = True
    check("helper: apply() refuses a wrong-length list before calling the server", raised)
    check("helper: model() collects every property of reactor/segments/loops",
          hm["reactor"] == {"RatedOutput_MW": 100.0} and set(hm["segments"]) == {"FWD", "AFT"}
          and all("Capacity_MW" in v for v in hm["segments"].values())
          and all("Capacity_MWth" in v for v in hm["loops"].values()))
    await pmc7.disconnect()
    src = open(os.path.join(dist, "pmc7.py")).read().lower()
    tells = [t for t in ("flag{", "aux_bus_7", "tamper", "rig", "shadow", "dual", "marginal", "linprog", "spec")
             if re.search(rf"\b{re.escape(t)}", src)]
    check("leak: dist/pmc7.py has no flag and no solve/tamper hints", not tells, str(tells))

    bad = 0
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
        bad += not ok
    print(f"\n{len(checks)-bad}/{len(checks)} passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    asyncio.run(main())
