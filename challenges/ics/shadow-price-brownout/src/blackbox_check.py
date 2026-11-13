"""Black-box resistance check (GM-only).

Attacks ApplyDispatch using only what its report reveals (efficiency, alarm and
fault amounts), with the real server.evaluate() offline, no network. Question
it answers: can a generic optimizer reach the flags without solving the LP?

Result 2026-09-22: Powell (3,962 calls, 76.85 %), SLSQP penalty (stalled after
18) and differential evolution (38,523 calls, 82.99 %) reached neither flag.
Flag II is out of reach by construction: the true optimum starves aux_bus_7,
which the report shows as an ALARM, so "maximize efficiency without alarms"
settles at the 87.5 % Part I answer.

    uv run --with asyncua==2.0.1 --with scipy python blackbox_check.py .   (from src/, after bake.py)
"""
import re, sys, json
import numpy as np
from scipy.optimize import differential_evolution, minimize
sys.path.insert(0, sys.argv[1])
import server                                    # evaluate() = the real server logic
caps = np.array([l["cap"] for l in server.BAKED["loads"]])     # readable from the model
calls = {"n": 0, "first_I": None, "first_II": None, "best_ok_eff": 0.0}

def feedback(x):
    calls["n"] += 1
    rep, eff, flags = server.evaluate(list(x))
    viol = sum(float(v) for v in re.findall(r"(?:short|\+)\s*([\d.]+)", rep))
    if "I" in flags and calls["first_I"] is None: calls["first_I"] = calls["n"]
    if "II" in flags and calls["first_II"] is None: calls["first_II"] = calls["n"]
    if viol == 0: calls["best_ok_eff"] = max(calls["best_ok_eff"], eff)
    return eff, viol

def f(x):
    eff, viol = feedback(x)
    return -eff + 50.0 * viol                   # maximise efficiency, punish every reported alarm/fault

def run(label, go):
    calls.update(n=0, first_I=None, first_II=None, best_ok_eff=0.0)
    go()
    print(f"{label:34} calls={calls['n']:6}  flag I at call {calls['first_I']}  "
          f"flag II at call {calls['first_II']}  best alarm-free eff={calls['best_ok_eff']:.2f}%")

bounds = [(0, c) for c in caps]
x0 = np.array([c / 2 for c in caps])
run("Powell (derivative-free)", lambda: minimize(f, x0, method="Powell", bounds=bounds, options={"maxfev": 20000}))
run("SLSQP w/ penalty (finite diff)", lambda: minimize(f, x0, method="SLSQP", bounds=bounds, options={"maxiter": 500}))
run("differential evolution", lambda: differential_evolution(f, bounds, maxiter=150, seed=1, tol=1e-9, polish=True))
