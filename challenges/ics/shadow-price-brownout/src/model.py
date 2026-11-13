"""Shadow Price — canonical model data and LP helpers (GM-only).

Single source of truth for the numbers. Imported by:
  shadow_price_lp.py  design checks (scipy)
  bake.py             writes baked.json for the server at image build time

The server itself never imports this module (no scipy at runtime).

Model: maximize sum(w_i x_i) subject to
  reactor:  sum x_i                      <= R
  seg_S:    sum_{i in S} x_i             <= SEG[S]
  loop_L:   sum_{i in L} c_i x_i         <= LOOP[L]
  floor_i:  x_i                          >= f_i   (rows, so players see them as constraints)
  cap_i:    x_i                          <= u_i
  x >= 0
"""
import numpy as np
from scipy.optimize import linprog

R = 100.0
SEG = {"FWD": 60.0, "AFT": 58.0}
LOOP = {"A": 42.0, "B": 30.0}

# name: (segment, loop, coolant c, weight w, floor f, cap u, description)
LOADS = {
    "life_support":   ("FWD", "A", 0.3, 0.2, 18.0, 30.0, "atmosphere, thermal, O2"),
    "thrusters":      ("AFT", "A", 0.5, 2.8, 10.0, 40.0, "main drive + RCS"),
    "shields":        ("FWD", "B", 0.9, 4.4, 8.0, 32.0, "deflector array"),
    "comms":          ("FWD", "A", 0.2, 1.3, 3.0, 8.0, "long-range comms"),
    "payload_stasis": ("AFT", "B", 0.6, 1.9, 9.0, 12.0, "payload stasis"),
    "aux_bus_1":  ("FWD", "A", 0.3, 0.30, 2.0, 4.0, "galley"),
    "aux_bus_2":  ("AFT", "A", 0.5, 0.35, 6.5, 9.0, "hydroponics bay"),
    "aux_bus_3":  ("FWD", "B", 0.4, 0.10, 1.2, 3.0, "hull lighting"),
    "aux_bus_4":  ("AFT", "A", 0.7, 0.20, 0.0, 6.0, "cargo crane"),
    "aux_bus_5":  ("FWD", "A", 0.6, 0.40, 1.5, 3.0, "sensor mast"),
    "aux_bus_6":  ("AFT", "A", 0.4, 0.30, 3.5, 5.0, "water recycler"),
    "aux_bus_7":  ("AFT", "B", 1.0, 0.10, 0.0, 8.0, "cargo hold 3 environmental"),
    "aux_bus_8":  ("FWD", "A", 0.3, 0.35, 2.5, 4.0, "medbay"),
    "aux_bus_9":  ("AFT", "A", 1.2, 0.20, 0.0, 5.0, "fabricator"),
    "aux_bus_10": ("FWD", "B", 0.8, 0.20, 2.0, 3.0, "sensor heaters"),
    "aux_bus_11": ("AFT", "A", 0.5, 0.25, 4.0, 6.0, "air scrubbers"),
    "aux_bus_12": ("AFT", "B", 0.7, 0.30, 1.5, 3.0, "nav computer"),
}
PRIMARIES = ["life_support", "thrusters", "shields", "comms", "payload_stasis"]
SPEC_FLOORS = {k: LOADS[k][4] for k in PRIMARIES}   # what the brief publishes

# The two tamperings in the served model.
TAMPER_II_FLOOR = 5.5                               # aux_bus_7 floor (true: 0)
TAMPER_I_SENSE = {"life_support": "LE"}             # floor sense flipped (true: GE)

# ApplyDispatch validator tolerances.
FEAS_TOL = 0.05      # MW / MWth per constraint row
OBJ_TOL = 0.002      # relative to the threshold objective

NAMES = list(LOADS)
LOAD_ORDER_NOTE = "ApplyDispatch takes one Allocation_MW value per load, in this order."
N = len(NAMES)
IDX = {k: i for i, k in enumerate(NAMES)}
WEIGHTS = np.array([LOADS[k][3] for k in NAMES])


def true_floors():
    return {k: LOADS[k][4] for k in NAMES}


def served_floors():
    f = true_floors()
    f["aux_bus_7"] = TAMPER_II_FLOOR
    return f


def build(floors, floor_sense=None):
    """Rows: (name, coeff vector, rhs), all as a.x <= b. floor_sense flips a floor to <=."""
    floor_sense = floor_sense or {}
    rows = [("reactor", np.ones(N), R)]
    for s, cap in SEG.items():
        rows.append((f"seg_{s}", np.array([1.0 if LOADS[k][0] == s else 0.0 for k in NAMES]), cap))
    for l, cap in LOOP.items():
        rows.append((f"loop_{l}", np.array([LOADS[k][2] if LOADS[k][1] == l else 0.0 for k in NAMES]), cap))
    for k in NAMES:
        f = floors[k]
        if f > 0:
            e = np.zeros(N); e[IDX[k]] = 1.0
            if floor_sense.get(k) == "LE":       # tampered: x <= f
                rows.append((f"floor_{k}", e, f))
            else:                               # x >= f  ->  -x <= -f
                rows.append((f"floor_{k}", -e, -f))
    for k in NAMES:
        e = np.zeros(N); e[IDX[k]] = 1.0
        rows.append((f"cap_{k}", e, LOADS[k][5]))
    return rows


def true_rows():
    return build(true_floors())


def served_rows():
    return build(served_floors(), floor_sense=TAMPER_I_SENSE)


def sign_fixed_rows():
    return build(served_floors())


def solve(rows):
    A = np.array([r[1] for r in rows]); b = np.array([r[2] for r in rows])
    res = linprog(-WEIGHTS, A_ub=A, b_ub=b, bounds=[(0, None)] * N, method="highs")
    assert res.status == 0, res.message
    x = res.x
    return dict(x=x, z=float(WEIGHTS @ x), slack=b - A @ x,
                duals=-res.ineqlin.marginals,      # shadow price for the max problem, >= 0
                lower=res.lower.marginals,         # reduced cost on x >= 0
                rows=rows, A=A, b=b)


def unique_vertex(sol):
    """Nondegenerate + strictly complementary => unique primal and unique dual."""
    active_rows = [i for i, s in enumerate(sol["slack"]) if abs(s) < 1e-7]
    active_bnds = [j for j, v in enumerate(sol["x"]) if abs(v) < 1e-7]
    n_active = len(active_rows) + len(active_bnds)
    zero_mult = [sol["rows"][i][0] for i in active_rows if sol["duals"][i] < 1e-7] + \
                [NAMES[j] for j in active_bnds if sol["lower"][j] < 1e-7]
    return n_active == N and not zero_mult, n_active, zero_mult


def violations(x, rows, tol=1e-4):
    return [(name, float(a @ x - b)) for name, a, b in rows if a @ x - b > tol]
