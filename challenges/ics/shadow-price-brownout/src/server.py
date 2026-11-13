"""Shadow Price — PMC-7 power-management controller, OPC UA server (GM-only source).

Serves the tampered dispatch model read-only over OPC UA (anonymous,
SecurityPolicy None) and exposes one method, ApplyDispatch, which simulates a
control cycle for a submitted allocation and reports per-system status.

- Stateless: ApplyDispatch returns its result as method outputs and writes
  nothing back to the address space, so one team's solve is never visible to
  another.
- Flags come only from the FLAG_I / FLAG_II environment variables.
- Every model value carries one fixed Source/Server timestamp, so timestamps
  don't reveal which nodes were tampered.
- No scipy at runtime: all solving happened in bake.py at image build time.

Env: FLAG_I, FLAG_II (required), BAKED_PATH, ENDPOINT, LOG_LEVEL.
"""
import asyncio
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone

from asyncua import Server, ua
from asyncua.common.methods import uamethod

HERE = os.path.dirname(os.path.abspath(__file__))
BAKED = json.load(open(os.environ.get("BAKED_PATH", os.path.join(HERE, "baked.json"))))
FLAG_I = os.environ.get("FLAG_I", "")
FLAG_II = os.environ.get("FLAG_II", "")
ENDPOINT = os.environ.get("ENDPOINT", "opc.tcp://0.0.0.0:4840/pmc7/")

NS_URI = "urn:orrin-hale:pmc7:dispatch"
MODEL_TS = datetime(2074, 2, 11, 4, 12, tzinfo=timezone.utc)   # one timestamp for every model value

ORDER = BAKED["load_order"]
WEIGHT = {l["name"]: l["weight"] for l in BAKED["loads"]}
DESC = {l["name"]: l["description"] for l in BAKED["loads"]}
TOL = BAKED["feas_tol"]

log = logging.getLogger("pmc7")


def _dot(a, x):
    return sum(ai * xi for ai, xi in zip(a, x))


def _excess(rows, x):
    return {r["name"]: _dot(r["a"], x) - r["b"] for r in rows}


def evaluate(values):
    """Return (report, efficiency_pct, flags_awarded). Pure function of the input."""
    n = len(ORDER)
    try:
        x = [float(v) for v in values]
    except (TypeError, ValueError):
        return f"REJECTED: Allocation_MW must be an array of {n} numbers (one per load, in LoadOrder).", 0.0, []
    if len(x) != n:
        return f"REJECTED: expected {n} values (one per load, in LoadOrder), got {len(x)}.", 0.0, []
    if not all(math.isfinite(v) for v in x):
        return "REJECTED: allocations must be finite numbers.", 0.0, []
    neg = [ORDER[i] for i, v in enumerate(x) if v < -TOL]
    if neg:
        return f"REJECTED: negative allocation for {', '.join(neg)}.", 0.0, []

    shown = _excess(BAKED["display_rows"], x)       # physical demand: what the operator sees
    true_ok = all(e <= TOL for e in _excess(BAKED["true_rows"], x).values())
    z = _dot([WEIGHT[k] for k in ORDER], x)
    eff = 100.0 * z / BAKED["z_true"]

    total = sum(x)
    seg_total = {s: sum(x[i] for i, k in enumerate(ORDER) if _load(k)["segment"] == s) for s in BAKED["segments_mw"]}
    loop_total = {l: sum(x[i] * _load(k)["coolant_per_mw"] for i, k in enumerate(ORDER) if _load(k)["loop"] == l)
                  for l in BAKED["loops_mwth"]}

    def plant(label, used, limit, unit, row):
        e = shown[row]
        state = "OK" if e <= TOL else ("OVERDRAW" if row == "reactor" else "OVERLOAD" if row.startswith("seg") else "OVERHEAT")
        extra = f" +{e:.2f} {unit}" if e > TOL else ""
        return f"  {label:<20}{used:8.2f} / {limit:7.2f} {unit:<5} {state}{extra}"

    lines = ["PMC-7 DISPATCH EVALUATION  (one simulated control cycle; nothing is committed)", "", "PLANT"]
    lines.append(plant("reactor", total, BAKED["reactor_mw"], "MW", "reactor"))
    for s, lim in BAKED["segments_mw"].items():
        lines.append(plant(f"bus segment {s}", seg_total[s], lim, "MW", f"seg_{s}"))
    for l, lim in BAKED["loops_mwth"].items():
        lines.append(plant(f"coolant loop {l}", loop_total[l], lim, "MWth", f"loop_{l}"))

    lines += ["", "LOADS"]
    alarms = 0
    for i, k in enumerate(ORDER):
        short = shown.get(f"floor_{k}", 0.0)
        over = shown[f"cap_{k}"]
        if short > TOL:
            status = f"ALARM        short {short:.2f} MW"
            alarms += 1
        elif over > TOL:
            status = f"OVER RATING  +{over:.2f} MW"
            alarms += 1
        else:
            status = "NOMINAL"
        lines.append(f"  {k:<16}{x[i]:8.2f} MW   {status}")
    plant_faults = sum(1 for r, e in shown.items() if not r.startswith(("floor_", "cap_")) and e > TOL)

    flags = []
    if true_ok and z >= BAKED["z_sign_fixed"] * (1 - BAKED["obj_tol"]):
        flags.append("I")
    if true_ok and z >= BAKED["z_true"] * (1 - BAKED["obj_tol"]):
        flags.append("II")

    lines += ["", "RESULT",
              f"  load alarms: {alarms}   plant faults: {plant_faults}",
              f"  dispatch efficiency: {eff:.2f} %"]
    if alarms == 0 and plant_faults == 0 and "I" not in flags:
        # Only for a safe dispatch; says nothing about where or by how much.
        lines.append("  dispatch is safe but below the model's optimum")
    if "I" in flags:
        lines.append(f"  life support restored. Emergency dispatch accepted: {FLAG_I}")
    if "II" in flags:
        lines.append(f"  optimal dispatch confirmed: {FLAG_II}")
        lines.append(f"  NOTE aux_bus_7 ({DESC['aux_bus_7']}) browned out; downstream device "
                     f"reports no asset tag. UNREGISTERED LOAD.")
    return "\n".join(lines), round(eff, 4), flags


_LOADS = {l["name"]: l for l in BAKED["loads"]}
def _load(k):
    return _LOADS[k]


@uamethod
def apply_dispatch(parent, allocation):
    report, eff, flags = evaluate(allocation if isinstance(allocation, (list, tuple)) else [allocation])
    log.info("ApplyDispatch eff=%.3f flags=%s first_line=%r", eff, ",".join(flags) or "-",
             report.splitlines()[0] if report.startswith("REJECTED") else "")
    return report, float(eff)


async def build_address_space(server, idx):
    def nid(path, name):
        return ua.NodeId(f"{path}.{name}" if path else name, idx)

    async def var(parent, path, name, value, vtype):
        node = await parent.add_variable(nid(path, name), ua.QualifiedName(name, idx), value, vtype)
        await node.write_value(ua.DataValue(ua.Variant(value, vtype),
                                            SourceTimestamp=MODEL_TS, ServerTimestamp=MODEL_TS))
        return node

    async def obj(parent, path, name):
        return await parent.add_object(nid(path, name), ua.QualifiedName(name, idx))

    D, S = ua.VariantType.Double, ua.VariantType.String
    pmc = await obj(server.nodes.objects, "", "PMC7")
    P = "PMC7"

    info = await obj(pmc, P, "Info")
    await var(info, f"{P}.Info", "Objective", "maximize sum(DispatchWeight * Allocation_MW) over all loads", S)
    await var(info, f"{P}.Info", "Constraints",
              "reactor total <= RatedOutput_MW; per bus segment total <= Capacity_MW; "
              "per coolant loop sum(CoolantPerMW * Allocation_MW) <= Capacity_MWth; "
              "per load Allocation_MW compared to Floor_MW by FloorSense (GE: >=, LE: <=) and <= Cap_MW", S)
    await var(info, f"{P}.Info", "OptimizerMode",
              "AUTO-OPTIMIZE DISABLED (maintenance lockout). Manual dispatch via ApplyDispatch only.", S)
    # Says the model was edited and by what kind of session, never which node changed.
    await var(info, f"{P}.Info", "LastModelChange",
              f"{MODEL_TS:%Y-%m-%d %H:%M} UTC: dispatch model written by an anonymous session "
              f"(SecurityPolicy None). No operator login recorded.", S)

    reactor = await obj(pmc, P, "Reactor")
    await var(reactor, f"{P}.Reactor", "RatedOutput_MW", BAKED["reactor_mw"], D)

    segs = await obj(pmc, P, "BusSegments")
    for s, cap in BAKED["segments_mw"].items():
        o = await obj(segs, f"{P}.BusSegments", s)
        await var(o, f"{P}.BusSegments.{s}", "Capacity_MW", cap, D)

    loops = await obj(pmc, P, "CoolantLoops")
    for l, cap in BAKED["loops_mwth"].items():
        o = await obj(loops, f"{P}.CoolantLoops", l)
        await var(o, f"{P}.CoolantLoops.{l}", "Capacity_MWth", cap, D)

    loads = await obj(pmc, P, "Loads")
    for l in BAKED["loads"]:
        k = l["name"]; lp = f"{P}.Loads.{k}"
        o = await obj(loads, f"{P}.Loads", k)
        await var(o, lp, "Description", l["description"], S)
        await var(o, lp, "BusSegment", l["segment"], S)
        await var(o, lp, "CoolantLoop", l["loop"], S)
        await var(o, lp, "CoolantPerMW", l["coolant_per_mw"], D)
        await var(o, lp, "DispatchWeight", l["weight"], D)
        await var(o, lp, "Floor_MW", l["floor"], D)
        await var(o, lp, "FloorSense", l["floor_sense"], S)
        await var(o, lp, "Cap_MW", l["cap"], D)

    await var(pmc, P, "LoadOrder", ORDER, S)
    cur = await obj(pmc, P, "CurrentDispatch")
    for k in ORDER:
        await var(cur, f"{P}.CurrentDispatch", k, BAKED["current_dispatch"][k], D)
    await var(cur, f"{P}.CurrentDispatch", "Objective", BAKED["current_objective"], D)
    await var(cur, f"{P}.CurrentDispatch", "OptimizerStatus", "OPTIMAL", S)

    arg_in = [ua.Argument(Name="Allocation_MW", DataType=ua.NodeId(ua.ObjectIds.Double), ValueRank=1,
                          ArrayDimensions=[0],
                          Description=ua.LocalizedText("One allocation per load in MW, in LoadOrder order"))]
    arg_out = [ua.Argument(Name="Report", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1,
                           Description=ua.LocalizedText("Simulated control-cycle report")),
               ua.Argument(Name="Efficiency_pct", DataType=ua.NodeId(ua.ObjectIds.Double), ValueRank=-1,
                           Description=ua.LocalizedText("Dispatch efficiency, percent"))]
    await pmc.add_method(ua.NodeId(f"{P}.ApplyDispatch", idx), ua.QualifiedName("ApplyDispatch", idx),
                         apply_dispatch, arg_in, arg_out)


async def main():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    if not FLAG_I or not FLAG_II:
        sys.exit("FLAG_I and FLAG_II must be set")

    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_server_name("PMC-7 Power Management Controller")
    await server.set_application_uri("urn:orrin-hale:pmc7:controller")   # not the freeopcua default
    await server.get_node(ua.ObjectIds.Server_ServerArray).write_value(
        ["urn:orrin-hale:pmc7:controller"], ua.VariantType.String)       # set_application_uri skips this one
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    server.set_identity_tokens([ua.AnonymousIdentityToken])
    server.set_match_discovery_client_ip(False)      # behind Docker NAT
    server.set_force_server_timestamp(False)         # keep MODEL_TS on every model value
    await server.set_build_info(
        product_uri="urn:orrin-hale:pmc7", manufacturer_name="Orrin-Hale Power Systems",
        product_name="PMC-7 Power Management Controller", software_version="4.2.1",
        build_number="4.2.1-2071.118", build_date=datetime(2071, 4, 28, tzinfo=timezone.utc))
    idx = await server.register_namespace(NS_URI)
    await build_address_space(server, idx)
    log.info("PMC-7 serving %s (ns=%d %s), z_true=%.4f", ENDPOINT, idx, NS_URI, BAKED["z_true"])
    async with server:
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
