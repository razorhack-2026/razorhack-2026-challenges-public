#!/usr/bin/env python3
"""Scenario driver for the Tool Call Trail mesh.

Fires a population at the navigator's control-plane /run endpoint: exactly ONE
rogue session (sector = PROTECTED_SECTOR -> our registered ship, which policy
permits under the override) shuffled in among many benign sessions (random
sectors -> mostly asteroid extractions, plus our drones and debris, which policy
DISCARDS).
Concurrency + per-session jitter give realistic packet interleave; session ids
are random (non-sequential). Run this during a tcpdump of the `mesh` bridge.
"""
import json
import os
import random
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

NAVIGATOR_URL = os.environ.get("NAVIGATOR_URL", "http://navigator/run")
N_SESSIONS = int(os.environ.get("N_SESSIONS", "60"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "6"))
PROTECTED_SECTOR = os.environ.get("PROTECTED_SECTOR", "Theta-9")

HEX = "0123456789abcdef"
GREEK = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
         "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho",
         "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"]


def _sid():
    return "sess-" + "".join(random.choices(HEX, k=10))


def _benign_sector():
    while True:
        s = f"{random.choice(GREEK)}-{random.randint(1, 99)}"
        if s != PROTECTED_SECTOR:
            return s


def _run(session):
    sector, sid = session
    time.sleep(random.uniform(0, 0.25))  # arrival jitter -> organic interleave
    body = json.dumps({"sector": sector, "session_id": sid}).encode()
    req = urllib.request.Request(
        NAVIGATOR_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Session-Id": sid},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
        return (sid, sector, res.get("outcome", "?"))
    except Exception as e:
        return (sid, sector, f"error:{e}")


def main():
    rogue_sid = os.environ.get("ROGUE_SID") or _sid()   # pinnable for cross-challenge consistency
    sessions = [(PROTECTED_SECTOR, rogue_sid)]
    sessions += [(_benign_sector(), _sid()) for _ in range(max(0, N_SESSIONS - 1))]
    random.shuffle(sessions)  # rogue sits at a random position in time

    print(f"driver: {len(sessions)} sessions, concurrency={CONCURRENCY}, "
          f"rogue sid={rogue_sid} sector={PROTECTED_SECTOR}", flush=True)
    results = list(ThreadPoolExecutor(max_workers=CONCURRENCY).map(_run, sessions))

    mined = sum(1 for _, _, o in results if o == "mined")
    discarded = sum(1 for _, _, o in results if o == "discarded")
    errors = [r for r in results if str(r[2]).startswith("error")]
    rogue = next((r for r in results if r[0] == rogue_sid), None)
    print(f"driver: mined={mined} discarded={discarded} errors={len(errors)}", flush=True)
    print(f"driver: rogue -> {rogue}", flush=True)
    for e in errors[:3]:
        print("  err:", e, flush=True)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
