# Shadow Price: Brownout

**Category:** ICS · **Difficulty:** easy

Life support on the *Keeper of Tomorrow* just dropped to 2 MW, and the power-management controller says that's optimal.

The PMC-7 splits the reactor's output between the ship's systems by solving an economic-dispatch problem: maximize the value of the power delivered, subject to the reactor, bus-segment and coolant-loop limits and each load's floor and cap. Its model sits on the ship's control network over OPC UA. The auto-optimizer has been locked out since the last maintenance cycle, so the only way to change the dispatch is to work one out yourself and apply it through the controller. The model changed during that lockout. Nobody on the crew changed it.

The mission spec is the authority on minimum safe draw for the primary systems:

| System | Minimum safe draw |
|---|---|
| `life_support` | 18 MW |
| `thrusters` | 10 MW |
| `shields` | 8 MW |
| `comms` | 3 MW |
| `payload_stasis` | 9 MW |

Get life support back, and give the ship the best dispatch the corrected model allows.

**Connect:** `opc.tcp://<host>:4840/pmc7/` (anonymous, no security)

**Files:** `pmc7.py`, a small client helper.

**Getting started.** `pmc7.py` handles the OPC UA plumbing: connecting, browsing, reading values and submitting a dispatch. From the folder you saved it in:

```
uv run --with asyncua==2.0.1 python -m asyncio     # or: pip install asyncua==2.0.1
>>> from pmc7 import *
>>> pmc = await connect("opc.tcp://<host>:4840/pmc7/")
>>> await tree(pmc)
```

Its docstring covers the rest (`val`, `kids`, `model`, `apply`). Any other OPC UA client works too.

Part 1 of the Shadow Price chain. Unlocks: Shadow Price: Dead Weight.
