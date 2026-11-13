"""pmc7.py: client helpers for the PMC-7 power-management controller (OPC UA).

Plumbing only: connect, browse, read values, and submit a dispatch. It doesn't
solve anything for you.

Needs the `asyncua` package, version 2.0.1 (what the controller runs). The
easiest way to use it is an async Python prompt, where `await` works directly.
Run this from the folder holding pmc7.py:

    uv run --with asyncua==2.0.1 python -m asyncio     (or: pip install asyncua==2.0.1; python -m asyncio)

    >>> from pmc7 import *
    >>> pmc = await connect("opc.tcp://<host>:4840/pmc7/")
    >>> await tree(pmc)                          # print everything the controller exposes
    >>> await kids(pmc, "Loads")                 # child names under a node
    >>> await val(pmc, "Info", "Objective")      # one value, by browse path
    >>> m = await model(pmc)                     # every model node's properties, as plain dicts
    >>> report, eff = await apply(pmc, m["current_dispatch"])   # simulate a dispatch
    >>> print(report)
    >>> await disconnect()

`apply` takes either a dict {load_name: MW} covering every load, or a list of
MW values in LoadOrder order. Nothing you submit is committed to the ship; each
call simulates one control cycle and reports back.

In a script, put the same calls inside `async def main():` and finish with
`asyncio.run(main())`.

Prompt tip: after a line starting with `def`, `async def` or `for`, press Enter
on an empty line before typing the next statement.
"""
from asyncua import Client, ua

__all__ = ["connect", "disconnect", "val", "kids", "tree", "model", "apply"]

NS = 2                      # the controller's namespace index (urn:orrin-hale:pmc7:dispatch)
_client = None


async def connect(url):
    """Connect anonymously and return the PMC7 root node."""
    global _client
    _client = Client(url=url)
    await _client.connect()
    return await _client.nodes.objects.get_child(f"{NS}:PMC7")


async def disconnect():
    global _client
    if _client is not None:
        await _client.disconnect()
        _client = None


async def _node(pmc, *path):
    return await pmc.get_child([f"{NS}:{p}" for p in path]) if path else pmc


async def val(pmc, *path):
    """Read one value: await val(pmc, "Reactor", "RatedOutput_MW")."""
    return await (await _node(pmc, *path)).read_value()


async def kids(pmc, *path):
    """Child browse names: await kids(pmc, "Loads", "thrusters")."""
    return [(await n.read_browse_name()).Name for n in await (await _node(pmc, *path)).get_children()]


async def tree(pmc, *path, depth=6):
    """Print the address space below a node: values, method signatures, and any
    Description attributes. Prints "..." wherever the depth limit cuts it short."""
    async def desc(node, name):
        dv = await node.read_attribute(ua.AttributeIds.Description)
        text = dv.Value.Value.Text if dv.Value is not None and dv.Value.Value is not None else None
        return f"   # {text}" if text and text != name else ""

    async def walk(node, indent, left):
        for child in await node.get_children():
            name = (await child.read_browse_name()).Name
            cls = await child.read_node_class()
            note = await desc(child, name)
            below = [] if cls == ua.NodeClass.Method else await child.get_children()
            if cls == ua.NodeClass.Method:
                sig = {}
                for arg in await child.get_children():
                    sig[(await arg.read_browse_name()).Name] = ", ".join(
                        a.Name for a in (await arg.read_value() or []))
                print(f"{indent}{name}({sig.get('InputArguments', '')}) -> "
                      f"({sig.get('OutputArguments', '')})   [method]{note}")
                continue
            if cls == ua.NodeClass.Variable:
                print(f"{indent}{name} = {await child.read_value()!r}{note}")
            else:
                print(f"{indent}{name}/{note}")
            if below:
                if left > 1:
                    await walk(child, indent + "  ", left - 1)
                else:
                    print(f"{indent}  ...   ({len(below)} more below; raise depth=)")
    await walk(await _node(pmc, *path), "", depth)


async def model(pmc):
    """Read the whole dispatch model into plain Python dicts.

    Returns {"reactor", "segments", "loops", "load_order", "loads",
    "current_dispatch"}. Every node's properties are collected exactly as the
    controller reports them, e.g. m["reactor"]["RatedOutput_MW"],
    m["segments"]["FWD"]["Capacity_MW"], m["loads"]["thrusters"]["Cap_MW"].
    """
    async def props(*path):
        return {p: await val(pmc, *path, p) for p in await kids(pmc, *path)}

    order = await val(pmc, "LoadOrder")
    return {
        "reactor": await props("Reactor"),
        "segments": {s: await props("BusSegments", s) for s in await kids(pmc, "BusSegments")},
        "loops": {l: await props("CoolantLoops", l) for l in await kids(pmc, "CoolantLoops")},
        "load_order": order,
        "loads": {k: await props("Loads", k) for k in order},
        "current_dispatch": {k: await val(pmc, "CurrentDispatch", k) for k in order},
    }


async def apply(pmc, dispatch):
    """Simulate a dispatch through ApplyDispatch. Returns (report, efficiency_pct).

    dispatch: {load_name: MW} covering every load, or a list in LoadOrder order.
    """
    order = await val(pmc, "LoadOrder")
    if isinstance(dispatch, dict):
        missing = [k for k in order if k not in dispatch]
        extra = [k for k in dispatch if k not in order]
        if missing or extra:
            raise ValueError(f"dispatch must cover exactly the loads in LoadOrder "
                             f"(missing: {missing}, unknown: {extra})")
        values = [float(dispatch[k]) for k in order]
    else:
        values = [float(v) for v in dispatch]
        if len(values) != len(order):
            raise ValueError(f"expected {len(order)} values in LoadOrder order, got {len(values)}")
    report, eff = await pmc.call_method(f"{NS}:ApplyDispatch", ua.Variant(values, ua.VariantType.Double))
    return report, eff
