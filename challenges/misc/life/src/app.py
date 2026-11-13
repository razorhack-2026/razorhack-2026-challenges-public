"""
Minor Calculations (Misc, easy)

Each call to GET /api/status mints a fresh instance: a random id plus randomized
constraint constants. The player solves for N2 and O2 and POSTs them back with the
id to /api/mix. The instance is only valid for WINDOW_SECONDS, which is short
enough that the round trip has to be scripted.
"""
import os
import random
import time
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

FLAG = os.environ.get("LIFE_FLAG", "flag{l1f3_br3ath3_3a5y}")

# How long an issued instance stays valid. Deliberately too short to solve by hand.
WINDOW_SECONDS = float(os.environ.get("LIFE_WINDOW_SECONDS", "5"))
TOLERANCE = 0.05

# Instances are dropped this long after expiry so the dict cannot grow forever.
PURGE_AFTER = WINDOW_SECONDS + 60

# instance id -> issued timestamp and the randomized constants
INSTANCES: dict[str, dict] = {}


def _purge(now: float) -> None:
    for key in [k for k, v in INSTANCES.items() if now - v["issued_at"] > PURGE_AFTER]:
        INSTANCES.pop(key, None)


def _new_instance() -> tuple[str, dict]:
    """Randomize the constants so each instance has a different answer."""
    inst = {
        "ar": round(random.uniform(0.70, 1.30), 2),
        "trace": round(random.uniform(0.05, 0.60), 2),
        "k": random.choice([2, 3, 4]),
        "base": round(random.uniform(18.0, 22.0), 1),
        "issued_at": time.monotonic(),
    }
    return uuid.uuid4().hex, inst


def _solution(inst: dict) -> tuple[float, float]:
    o2 = inst["k"] * inst["trace"] + inst["base"]
    n2 = 100 - o2 - inst["ar"] - inst["trace"]
    return n2, o2


@app.route("/api/status")
def status():
    now = time.monotonic()
    _purge(now)
    instance_id, inst = _new_instance()
    INSTANCES[instance_id] = inst
    return jsonify(
        id=instance_id,
        expires_in_seconds=WINDOW_SECONDS,
        constraints=[
            "N2 + O2 + Ar + trace = 100",
            f"O2 = {inst['k']} * trace + {inst['base']}",
            f"Ar = {inst['ar']}",
            f"trace = {inst['trace']}",
        ],
        submit={
            "endpoint": "POST /api/mix",
            "body": {"id": instance_id, "N2": "<float>", "O2": "<float>"},
        },
        tolerance=TOLERANCE,
        hint=(
            "Constants change every request and this id expires in "
            f"{WINDOW_SECONDS:g}s."
        ),
    )


@app.route("/api/mix", methods=["POST"])
def mix():
    now = time.monotonic()
    _purge(now)

    body = request.get_json(silent=True) or {}
    instance_id = body.get("id")
    if not isinstance(instance_id, str) or not instance_id:
        return jsonify(error="missing id - request one from /api/status"), 400

    inst = INSTANCES.get(instance_id)
    if inst is None:
        return jsonify(error="unknown id - request a new one from /api/status"), 404

    elapsed = now - inst["issued_at"]
    if elapsed > WINDOW_SECONDS:
        INSTANCES.pop(instance_id, None)
        return jsonify(
            error="instance expired",
            elapsed_seconds=round(elapsed, 3),
            window_seconds=WINDOW_SECONDS,
            detail="the atmosphere drifted while you were solving - start over",
        ), 410

    try:
        n2 = float(body["N2"])
        o2 = float(body["O2"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="bad payload - expected numeric N2 and O2"), 400

    want_n2, want_o2 = _solution(inst)
    if abs(o2 - want_o2) > TOLERANCE:
        return jsonify(status="MIX_REJECTED", detail="O2 outside tolerance"), 200
    if abs(n2 - want_n2) > TOLERANCE:
        return jsonify(status="MIX_REJECTED", detail="N2 outside tolerance"), 200

    INSTANCES.pop(instance_id, None)
    return jsonify(
        status="ATMOSPHERE_STABLE",
        solved_in_seconds=round(elapsed, 3),
        flag=FLAG,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))
