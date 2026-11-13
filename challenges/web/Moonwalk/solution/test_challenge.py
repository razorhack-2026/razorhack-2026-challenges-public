#!/usr/bin/env python3
"""
Anti-cheese checks for MOONWALK. Runs against the Flask app in-process.

    python3 solution/test_challenge.py
"""
import concurrent.futures as cf
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import random
import threading
import time

import app as moonwalk


def correct(rnd):
    return [rnd["keymap"][row.index("#")] for row in rnd["rows"]]


def lane_plus_one(rnd):
    return [row.index("#") + 1 for row in rnd["rows"]]

PASS = 0
moonwalk.COUNTDOWN_MS = 0      # most checks skip the countdown; section 14 tests it


def check(name, cond):
    global PASS
    if not cond:
        raise SystemExit(f"FAIL: {name}")
    PASS += 1
    print(f"ok   {name}")


def fresh():
    moonwalk.STARTS.clear()
    c = moonwalk.app.test_client()
    assert c.post("/api/start", json={}).get_json()["ok"]
    return c


def session_of(c):
    return moonwalk.SESSIONS[c.get_cookie(moonwalk.COOKIE).value]


def answer(c, rnd, keys=None):
    keys = keys if keys is not None else correct(rnd)
    return c.post("/api/step", json={"nonce": rnd["nonce"], "keys": keys}).get_json()


# 1. no session / forged session
c = moonwalk.app.test_client()
check("round without a session is refused", c.post("/api/round", json={}).status_code == 401)
c.set_cookie(moonwalk.COOKIE, "forged-session-id")
check("forged session cookie is refused", c.post("/api/step", json={"nonce": "x", "keys": [1]}).status_code == 401)

# 2. honest play through a few rounds works
c = fresh()
for _ in range(5):
    rnd = c.post("/api/round", json={}).get_json()
    check(f"honest round {rnd['round']} accepted", answer(c, rnd)["ok"])

# 3. refetching a round returns the same round and does not reset the clock
c = fresh()
a = c.post("/api/round", json={}).get_json()
time.sleep(0.3)
b = c.post("/api/round", json={}).get_json()
check("refetch returns the same nonce and tiles", a["nonce"] == b["nonce"] and a["rows"] == b["rows"] and a["keymap"] == b["keymap"])
check("refetch does not restart the timer", b["remaining_ms"] <= a["remaining_ms"] - 250)

# 4. replaying an old answer kills the run
c = fresh()
r1 = c.post("/api/round", json={}).get_json()
good = {"nonce": r1["nonce"], "keys": correct(r1)}
check("first answer accepted", c.post("/api/step", json=good).get_json()["ok"])
c.post("/api/round", json={})
rep = c.post("/api/step", json=good)
check("replayed nonce rejected", rep.status_code == 409)
check("session dead after replay", c.post("/api/round", json={}).status_code == 410)

# 5. racing four different answers at once (one of them correct): at most one is processed
wins_total = 0
for trial in range(40):
    c = fresh()
    rnd = c.post("/api/round", json={}).get_json()
    cookie = c.get_cookie(moonwalk.COOKIE).value
    barrier = threading.Barrier(4)
    good_keys = correct(rnd)
    variants = [good_keys] + [[(k + d - 1) % 4 + 1 for k in good_keys] for d in (1, 2, 3)]
    random.shuffle(variants)

    def guess(i):
        cl = moonwalk.app.test_client()
        cl.set_cookie(moonwalk.COOKIE, cookie)
        barrier.wait()
        return cl.post("/api/step", json={"nonce": rnd["nonce"], "keys": variants[i]}).get_json()

    with cf.ThreadPoolExecutor(4) as ex:
        results = list(ex.map(guess, range(4)))
    oks = sum(1 for r in results if r.get("ok"))
    check_name = f"race trial {trial + 1}: {oks} of 4 concurrent guesses accepted"
    if oks > 1:
        raise SystemExit("FAIL: " + check_name)
    wins_total += oks
check(f"concurrent guesses never double-count (40 trials, {wins_total} lucky single wins)", True)

# 6. a wrong answer ends the run for good
c = fresh()
rnd = c.post("/api/round", json={}).get_json()
wrong = [k % 4 + 1 for k in correct(rnd)]
check("wrong keys rejected", not answer(c, rnd, wrong)["ok"])
check("dead session cannot fetch new rounds", c.post("/api/round", json={}).status_code == 410)
check("dead session cannot step", c.post("/api/step", json={"nonce": rnd["nonce"], "keys": wrong}).status_code == 410)

# 7. type confusion in the answer (each payload "means" the right keys)
cases = [
    ("bool", lambda k: [True if x == 1 else x for x in k] if 1 in k else [True] + k[1:]),
    ("float", lambda k: [float(x) for x in k]),
    ("string", lambda k: [str(x) for x in k]),
    ("joined string", lambda k: "".join(map(str, k))),
    ("nested list", lambda k: [[x] for x in k]),
    ("object", lambda k: {str(i): x for i, x in enumerate(k)}),
    ("null", lambda k: None),
    ("extra key", lambda k: k + [1]),
    ("empty", lambda k: []),
]
for name, make in cases:
    c = fresh()
    rnd = c.post("/api/round", json={}).get_json()
    payload = make(correct(rnd))
    res = c.post("/api/step", json={"nonce": rnd["nonce"], "keys": payload}).get_json()
    check(f"{name} answer {payload!r} rejected", not res["ok"])

# 8. late answers fail, measured on the server clock
saved = moonwalk.WINDOW_SCALE
moonwalk.WINDOW_SCALE = 0.02          # round 1 window becomes ~85 ms
c = fresh()
rnd = c.post("/api/round", json={}).get_json()
time.sleep(0.25)
res = answer(c, rnd)
check("late answer rejected", not res["ok"] and "too slow" in res["error"])
moonwalk.WINDOW_SCALE = saved

# 9. no way to skip ahead: stepping before a round exists does nothing useful
c = fresh()
r = c.post("/api/step", json={"nonce": "anything", "keys": [1]})
check("step before any round is refused", r.status_code == 409)

# 10. a finished session cannot be replayed for the flag
c = fresh()
while True:
    rnd = c.post("/api/round", json={}).get_json()
    res = answer(c, rnd)
    if res.get("done"):
        break
    assert res["ok"], res
check("full run returns the flag", res["flag"] == moonwalk.FLAG)
check("finished session is closed", c.post("/api/round", json={}).status_code == 410)

# 11. session launches are rate limited per IP
moonwalk.STARTS.clear()
c = moonwalk.app.test_client()
codes = [c.post("/api/start", json={}).status_code for _ in range(moonwalk.STARTS_PER_MINUTE + 1)]
check("launch rate limit kicks in", codes[-1] == 429 and all(x == 200 for x in codes[:-1]))

# 12. a client cannot pick its own round or window
c = fresh()
rnd = c.post("/api/round", json={"round": 21, "window_ms": 999999}).get_json()
check("client-supplied round/window ignored", rnd["round"] == 1 and rnd["window_ms"] == moonwalk._window_ms(*moonwalk.ROUNDS[0]))

# 13. the key scramble: pressing lane+1 works early, then the keys get rewired
c = fresh()
for i in range(moonwalk.SCRAMBLE_FROM):
    rnd = c.post("/api/round", json={}).get_json()
    assert rnd["keymap"] == [1, 2, 3, 4]
    assert answer(c, rnd, lane_plus_one(rnd))["ok"]
check(f"rounds 1-{moonwalk.SCRAMBLE_FROM} use the plain 1-2-3-4 layout", True)
rnd = c.post("/api/round", json={}).get_json()
check(f"round {moonwalk.SCRAMBLE_FROM + 1} rewires the keys", rnd["keymap"] != [1, 2, 3, 4] and sorted(rnd["keymap"]) == [1, 2, 3, 4])
check("pressing lane+1 after the rewire fails", not answer(c, rnd, lane_plus_one(rnd))["ok"])

# 14. the countdown before each round
moonwalk.COUNTDOWN_MS = 400
c = fresh()
cd = c.post("/api/round", json={}).get_json()
check("countdown reveals the key layout", cd["countdown"] is True and sorted(cd["keymap"]) == [1, 2, 3, 4])
check("countdown hides the tiles and the nonce", "rows" not in cd and "nonce" not in cd)
time.sleep(0.15)
cd2 = c.post("/api/round", json={}).get_json()
check("re-requesting does not restart the countdown", cd2["starts_in_ms"] <= cd["starts_in_ms"] - 120)
real_nonce = session_of(c).pending["nonce"]
r = c.post("/api/step", json={"nonce": real_nonce, "keys": session_of(c).pending["answer"]})
check("even a correct answer during the countdown ends the run", r.status_code == 409
      and "before the round started" in r.get_json()["error"])
check("run is over after jumping the gun", c.post("/api/round", json={}).status_code == 410)

c = fresh()
c.post("/api/round", json={})
time.sleep(0.45)
rnd = c.post("/api/round", json={}).get_json()
check("tiles appear once the countdown ends", rnd["countdown"] is False and len(rnd["rows"]) == rnd["tile_count"])
check("the round clock starts at the end of the countdown", rnd["remaining_ms"] > rnd["window_ms"] - 150)
check("answering after the countdown works", answer(c, rnd)["ok"])
nxt = c.post("/api/round", json={}).get_json()
check("every round gets its own countdown", nxt["countdown"] is True and nxt["round"] == 2)
moonwalk.COUNTDOWN_MS = 0

print(f"\nall {PASS} checks passed")
