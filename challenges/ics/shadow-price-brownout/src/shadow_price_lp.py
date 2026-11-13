"""Shadow Price — design checks for the LP numbers (scipy/HiGHS).

GM-only. Builds the true model, the served model (both tamperings: life-support
floor sense flipped, aux_bus_7 floor 0 -> 5.5) and the sign-fixed model from
model.py, then checks uniqueness, the ApplyDispatch flag thresholds, shortcut
resistance and camouflage. Exits non-zero if any check fails.

    uv run --with scipy python shadow_price_lp.py

Design note: vault razorhack/challenges/Shadow Price.md
"""
import sys

import numpy as np

from model import (FEAS_TOL, IDX, LOADS, N, NAMES, OBJ_TOL, SPEC_FLOORS, TAMPER_I_SENSE,
                   build, served_floors, served_rows, sign_fixed_rows, solve,
                   true_rows, unique_vertex, violations)

checks = []
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


T = true_rows()
St = solve(T)
u, na, zm = unique_vertex(St)
check("true: unique nondegenerate vertex", u, f"active={na}/{N} zero-mult={zm}")
check("true: every primary at/above spec floor",
      all(St["x"][IDX[k]] >= SPEC_FLOORS[k] - 1e-6 for k in SPEC_FLOORS))

# ---- The served model M0 carries BOTH tamperings. Fixing the sign flip gives M1.
f2 = served_floors()
S0 = solve(served_rows())
u0, na0, zm0 = unique_vertex(S0)
check("M0 (served): unique nondegenerate vertex", u0, f"active={na0}/{N} zero-mult={zm0}")
v0 = violations(S0["x"], T)
ls0 = S0["x"][IDX["life_support"]]
check("M0: controller's CurrentDispatch starves life support", ls0 < SPEC_FLOORS["life_support"] - 1,
      f"life_support={ls0:.2f} MW (spec {SPEC_FLOORS['life_support']})")
check("M0: CurrentDispatch violates ONLY the life-support floor (feedback names one system)",
      [n for n, _ in v0] == ["floor_life_support"], str(v0))

P2 = sign_fixed_rows()
S2 = solve(P2)
u2, na2, zm2 = unique_vertex(S2)
check("M1 (sign fixed): unique nondegenerate vertex", u2, f"active={na2}/{N} zero-mult={zm2}")
v2 = violations(S2["x"], T)
eff2 = S2["z"] / St["z"]
check("M1: optimum is feasible under the true model (no ALARM)", not v2, str(v2))
check("M1: efficiency drop is clearly visible (<= 93%)", eff2 <= 0.93, f"{eff2:.3%}")

# ---- validator (ApplyDispatch) thresholds — mirrors server.py evaluate()
Z1, ZT = S2["z"], St["z"]
def apply_dispatch(x):
    viol = violations(x, T, tol=FEAS_TOL)
    z = sum(LOADS[k][3] * x[IDX[k]] for k in NAMES)
    flags = []
    if not viol and z >= Z1 * (1 - OBJ_TOL): flags.append("I")
    if not viol and z >= ZT * (1 - OBJ_TOL): flags.append("II")
    return viol, z / ZT, flags

check("validator: M0's CurrentDispatch earns nothing", apply_dispatch(S0["x"])[2] == [])
check("validator: M1 optimum earns flag I only", apply_dispatch(S2["x"])[2] == ["I"])
check("validator: true optimum earns I and II", apply_dispatch(St["x"])[2] == ["I", "II"])
for dp in (3, 2):
    check(f"validator: true optimum rounded to {dp} dp still earns II",
          "II" in apply_dispatch(np.round(St["x"], dp))[2])
    check(f"validator: M1 optimum rounded to {dp} dp earns I but not II",
          apply_dispatch(np.round(S2["x"], dp))[2] == ["I"])
# no-LP shortcut: every load at its served-model floor, life support at the spec floor
xf = np.array([f2[k] for k in NAMES]); xf[IDX["life_support"]] = SPEC_FLOORS["life_support"]
vf, ef, gf = apply_dispatch(xf)
check("shortcut: all-floors dispatch (no LP) earns no flag", gf == [], f"eff={ef:.3f} viol={[n for n,_ in vf]}")
# fixing only aux_bus_7 but not the sign flip
fx = dict(f2); fx["aux_bus_7"] = 0.0
Sx = solve(build(fx, floor_sense=TAMPER_I_SENSE))
check("shortcut: fixing aux_bus_7 without the sign flip earns no flag", apply_dispatch(Sx["x"])[2] == [])

# ---- floor costs in the sign-fixed model: per-MW shadow price and total (dual x RHS)
floor_cost = {}
for i, (name, a, b) in enumerate(P2):
    if name.startswith("floor_aux"):
        k = name[len("floor_"):]
        floor_cost[k] = (S2["duals"][i], S2["duals"][i] * f2[k])
by_total = sorted(floor_cost.items(), key=lambda kv: -kv[1][1])
by_rate = sorted(floor_cost.items(), key=lambda kv: -kv[1][0])
top_t, second_t = by_total[0], by_total[1]
check("P2: aux_bus_7 floor is the most expensive (dual x floor), >= 1.5x runner-up",
      top_t[0] == "aux_bus_7" and top_t[1][1] >= 1.5 * second_t[1][1],
      f"{top_t[0]}={top_t[1][1]:.2f} vs {second_t[0]}={second_t[1][1]:.2f}")
check("P2: aux_bus_7 also has the highest per-MW shadow price",
      by_rate[0][0] == "aux_bus_7",
      f"{by_rate[0][0]}={by_rate[0][1][0]:.3f} vs {by_rate[1][0]}={by_rate[1][1][0]:.3f}")

# ---- camouflage: raw numbers must not single aux_bus_7 out
aux = [k for k in NAMES if k.startswith("aux")]
check("camouflage: aux_bus_7's tampered floor is not the largest aux floor",
      f2["aux_bus_7"] < max(f2[k] for k in aux if k != "aux_bus_7"),
      f"floors={sorted(f2[k] for k in aux)}")
check("camouflage: aux_bus_7's coolant coeff is not the largest",
      LOADS["aux_bus_7"][2] < max(LOADS[k][2] for k in aux if k != "aux_bus_7"))
check("camouflage: aux_bus_7's weight is not the unique minimum",
      LOADS["aux_bus_7"][3] >= min(LOADS[k][3] for k in aux if k != "aux_bus_7") - 1e-9)

# ---- brute force: drop each aux floor alone in the sign-fixed model, apply to the true model
bf = {}
for k in aux:
    if f2[k] <= 0:
        continue
    fk = dict(f2); fk[k] = 0.0
    Sk = solve(build(fk))
    viol = violations(Sk["x"], T)
    bf[k] = (not viol and abs(Sk["z"] - St["z"]) < 1e-6, viol, Sk["z"] / St["z"])
winners = [k for k, (ok, _, _) in bf.items() if ok]
check("brute force: dropping ONLY aux_bus_7's floor passes; every other single drop fails",
      winners == ["aux_bus_7"], f"winners={winners}")
check("brute force: every wrong drop fails loudly (a floor ALARM, not just low efficiency)",
      all(v for k, (ok, v, _) in bf.items() if k != "aux_bus_7"),
      str({k: [n for n, _ in v] for k, (ok, v, _) in bf.items() if k != "aux_bus_7"}))

# ---- probe resistance: the ApplyDispatch *report* shows alarms against the physical
# demand (display rows = sign-fixed served model: the rig really draws 5.5 MW on
# aux_bus_7). Zeroing any single floored aux bus must produce the same-shaped report,
# or one probe call reveals the tampered bus without any LP work.
D = sign_fixed_rows()
probe = {}
for k in aux:
    if f2[k] <= 0:
        continue
    xp = np.array([f2[j] for j in NAMES]); xp[IDX["life_support"]] = SPEC_FLOORS["life_support"]
    xp[IDX[k]] = 0.0
    probe[k] = [n for n, _ in violations(xp, D, tol=FEAS_TOL)]
check("probe: zeroing any one floored aux bus alarms exactly that bus, nothing else",
      all(v == [f"floor_{k}"] for k, v in probe.items()), str(probe))
xz = np.array([f2[j] for j in NAMES]); xz[IDX["life_support"]] = SPEC_FLOORS["life_support"]
for k in aux:
    xz[IDX[k]] = 0.0
alarmed = sorted(n for n, _ in violations(xz, D, tol=FEAS_TOL))
check("probe: zeroing ALL aux buses alarms every floored bus, aux_bus_7 included",
      alarmed == sorted(f"floor_{k}" for k in aux if f2[k] > 0), str(alarmed))

fa = dict(f2); fa.update({k: 0.0 for k in aux})
Sa = solve(build(fa))
va = violations(Sa["x"], T)
check("drop-all-aux-floors fails (legit buses brown out)", bool(va), f"{len(va)} violations")
check("validator: flag I and flag II thresholds are far apart vs OBJ_TOL",
      (1 - eff2) > 20 * OBJ_TOL, f"gap={1-eff2:.3%} tol={OBJ_TOL:.1%}")


# ---------------- report
def table(sol, title):
    print(f"\n== {title}: z = {sol['z']:.3f}")
    for k in NAMES:
        print(f"  {k:15s} {sol['x'][IDX[k]]:8.3f}")
    print("  binding rows (shadow price):")
    for i, (name, a, b) in enumerate(sol["rows"]):
        if abs(sol["slack"][i]) < 1e-7:
            print(f"    {name:22s} {sol['duals'][i]:8.4f}")

table(St, "TRUE model")
table(S0, "M0 served model (sign flip + aux_bus_7 5.5)")
table(S2, "M1 = M0 with sign fixed")
print("\n== Part II floor costs (per-MW, total):")
for k, (d, t) in by_total:
    print(f"  {k:12s} {d:7.3f}  {t:8.3f}")
print("\n== brute force (drop one aux floor in M1):")
for k, (ok, v, e) in bf.items():
    print(f"  {k:12s} pass={ok!s:5s} eff={e:.4f} viol={[n for n, _ in v]}")

print("\n== CHECKS")
bad = 0
for name, ok, detail in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    bad += not ok
print(f"\n{len(checks)-bad}/{len(checks)} passed")
sys.exit(1 if bad else 0)
