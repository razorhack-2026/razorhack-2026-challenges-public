"""Bake the Shadow Price model into baked.json at image build time (GM-only).

Solves the served, sign-fixed and true models once with scipy and writes
everything server.py needs, so the running server has no scipy dependency and
does no solving at container start.

    python bake.py [out_path]      (default: baked.json next to this file)
"""
import json
import os
import sys

from model import (FEAS_TOL, IDX, LOAD_ORDER_NOTE, LOADS, LOOP, NAMES, OBJ_TOL, R, SEG,
                   TAMPER_I_SENSE, served_floors, served_rows, sign_fixed_rows, solve,
                   true_rows, unique_vertex)


def rows_json(rows):
    return [{"name": n, "a": [float(v) for v in a], "b": float(b)} for n, a, b in rows]


def main(out):
    served = solve(served_rows())
    fixed = solve(sign_fixed_rows())
    true = solve(true_rows())
    for label, sol in (("served", served), ("sign-fixed", fixed), ("true", true)):
        ok, n_active, zero_mult = unique_vertex(sol)
        assert ok, f"{label} model optimum is not a unique vertex ({n_active}, {zero_mult})"

    floors = served_floors()
    loads = []
    for k in NAMES:
        seg, loop, c, w, _, cap, desc = LOADS[k]
        loads.append({
            "name": k, "description": desc, "segment": seg, "loop": loop,
            "coolant_per_mw": c, "weight": w, "cap": cap,
            "floor": floors[k], "floor_sense": TAMPER_I_SENSE.get(k, "GE"),   # served (tampered)
        })

    baked = {
        "load_order": NAMES,
        "load_order_note": LOAD_ORDER_NOTE,
        "reactor_mw": R,
        "segments_mw": SEG,
        "loops_mwth": LOOP,
        "loads": loads,
        "current_dispatch": {k: round(float(served["x"][IDX[k]]), 4) for k in NAMES},
        "current_objective": round(served["z"], 4),
        # Flags are judged against the true model. The report's alarms are judged against
        # the physical demand (sign-fixed served model: the rig really draws 5.5 MW on
        # aux_bus_7), so starving aux_bus_7 alarms exactly like starving a legit bus.
        "true_rows": rows_json(true_rows()),
        "display_rows": rows_json(sign_fixed_rows()),
        "z_true": true["z"],
        "z_sign_fixed": fixed["z"],
        "feas_tol": FEAS_TOL,
        "obj_tol": OBJ_TOL,
    }
    with open(out, "w") as f:
        json.dump(baked, f, indent=1)
    print(f"baked {out}: z_true={true['z']:.4f} z_sign_fixed={fixed['z']:.4f} "
          f"current={served['z']:.4f} ({len(NAMES)} loads)")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "baked.json"))
