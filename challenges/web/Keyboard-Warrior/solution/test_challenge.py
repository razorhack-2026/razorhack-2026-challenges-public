#!/usr/bin/env python3
"""
Anti-cheese checks for MED BAY: Keyboard Warrior, run against the app in-process.

    python3 solution/test_challenge.py
"""
import concurrent.futures as cf
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import threading

import app as kw
from solve import INVISIBLE

PASS = 0


def check(name, cond):
    global PASS
    if not cond:
        raise SystemExit(f"FAIL: {name}")
    PASS += 1
    print(f"ok   {name}")


def fresh():
    kw.STARTS.clear()
    c = kw.app.test_client()
    assert c.post("/api/start", json={}).get_json()["ok"]
    return c


def session_of(c):
    return kw.SESSIONS[c.get_cookie(kw.COOKIE).value]


def attempt(c):
    return c.post("/api/level", json={}).get_json()


def submit(c, a, text):
    return c.post("/api/submit", json={"nonce": a["nonce"], "text": text})


def clean(a):
    return INVISIBLE.sub("", a["prompt"])


# ---- GM flag references stay synchronized without printing the value
challenge_dir = Path(__file__).resolve().parents[1]
metadata = (challenge_dir / "challenge.yml").read_text(encoding="utf-8")
solution_notes = Path(__file__).with_name("SOLUTION.md").read_text(encoding="utf-8")
configured = re.search(r"(?ms)^flags:\s*\r?\n\s*-\s*(flag\{[^}]+\})", metadata)
solution_flags = re.findall(r"(?i)flag\{[^}]+\}", solution_notes)
check("GM solution note matches challenge metadata",
      configured is not None and configured.group(1) == kw.FLAG and solution_flags == [kw.FLAG])


# ---- sessions
c = kw.app.test_client()
check("level without a session is refused", c.post("/api/level", json={}).status_code == 401)
c.set_cookie(kw.COOKIE, "forged")
check("forged cookie is refused", c.post("/api/submit", json={"nonce": "x", "text": "x"}).status_code == 401)

# ---- the client cannot choose its level or report its own score
c = fresh()
a = c.post("/api/level", json={"level": 5}).get_json()
check("client-requested level ignored", a["level"] == 1)
r = c.post("/api/submit", json={"nonce": a["nonce"], "text": "", "wpm": 999, "accuracy": 100,
                                "level": 5, "passed": True}).get_json()
check("client-reported wpm/accuracy/pass ignored", r["passed"] is False and r["accuracy"] == 0)

# ---- attempts are single use
c = fresh()
check("submit before any attempt is refused", submit(c, {"nonce": "x"}, "x").status_code == 409)
a = attempt(c)
check("honest level 1 passes", submit(c, a, clean(a)).get_json()["passed"])
check("replaying the same attempt is refused", submit(c, a, clean(a)).status_code == 409)
check("replay did not advance the level", session_of(c).level == 1)

c = fresh()
old = attempt(c)
new = attempt(c)
check("restarting a level invalidates the old attempt", submit(c, old, clean(old)).status_code == 409)
check("the new attempt still works", submit(c, new, clean(new)).get_json()["passed"])

# ---- racing the same attempt: only one submission is ever scored
for trial in range(20):
    c = fresh()
    a = attempt(c)
    cookie = c.get_cookie(kw.COOKIE).value
    gate = threading.Barrier(4)

    def go(_):
        cl = kw.app.test_client()
        cl.set_cookie(kw.COOKIE, cookie)
        gate.wait()
        return cl.post("/api/submit", json={"nonce": a["nonce"], "text": clean(a)}).get_json()

    with cf.ThreadPoolExecutor(4) as ex:
        results = list(ex.map(go, range(4)))
    scored = sum(1 for r in results if r.get("ok"))
    if scored != 1 or session_of(c).level != 1:
        raise SystemExit(f"FAIL: race trial {trial}: {scored} scored, level {session_of(c).level}")
check("4 concurrent submissions of one attempt: exactly one scored (20 trials)", True)

# ---- speed is measured on the server clock
c = fresh()
a = attempt(c)
session_of(c).attempt["issued"] -= 600          # pretend the player took 10 minutes
r = submit(c, a, clean(a)).get_json()
check("slow but perfect typing fails the speed target", not r["passed"] and r["wpm"] < r["required_wpm"])
check("failing does not advance the level", session_of(c).level == 0)

c = fresh()
a = attempt(c)
session_of(c).attempt["issued"] -= kw.ATTEMPT_TTL + 1
check("expired attempt refused", submit(c, a, clean(a)).status_code == 409)

# ---- accuracy is computed against the real prompt
c = fresh()
a = attempt(c)
t = clean(a)
sloppy = "".join(ch if i % 6 else "#" for i, ch in enumerate(t))
r = submit(c, a, sloppy).get_json()
check(f"fast but sloppy typing fails ({r['accuracy']}%)", not r["passed"])
c = fresh(); a = attempt(c)
check("empty answer fails", not submit(c, a, "").get_json()["passed"])
c = fresh(); a = attempt(c)
check("answer padded with junk fails", not submit(c, a, clean(a) + "x" * 200).get_json()["passed"])

# ---- type confusion and oversized bodies
for bad in ([1, 2], 123, None, {"t": "x"}, True):
    c = fresh(); a = attempt(c)
    r = c.post("/api/submit", json={"nonce": a["nonce"], "text": bad})
    check(f"text={bad!r} rejected", r.status_code == 400 and session_of(c).level == 0)
c = fresh(); a = attempt(c)
r = c.post("/api/submit", json={"nonce": a["nonce"], "text": "a" * 40000})
check("oversized body rejected", r.status_code == 413)

# ---- zero-width traps and final clearance
c = fresh()
for _ in range(3):
    a = attempt(c)
    assert submit(c, a, clean(a)).get_json()["passed"]
a = attempt(c)
check("fourth and final typing level is issued", a["level"] == 4)
check("final level prompt does not reveal the flag", kw.FLAG not in clean(a) and "flag" not in a)
original_rng = kw._rng
class AlwaysTrap:
    def random(self): return 0.0
    def choice(self, chars): return chars[0]
kw._rng = AlwaysTrap()
a = attempt(c)
kw._rng = original_rng
check("final prompt includes invisible formatting traps", a["prompt"] != clean(a))
r = submit(c, a, a["prompt"]).get_json()
check("verbatim copy fails exact final accuracy", not r["passed"] and "flag" not in r)
check("failed final attempt withholds the flag", "flag" not in r and kw.FLAG not in str(r))
a = attempt(c)
r = submit(c, a, clean(a)).get_json()
check("final level returns the exact configured flag", r.get("flag") == kw.FLAG)
check("final response returns the flag absent from its prompt", r.get("flag") == kw.FLAG and kw.FLAG not in clean(a))
check("participant page includes the completion screen", b"Typing test completed" in c.get("/").data)
check("finished session refuses new attempts", c.post("/api/level", json={}).status_code == 410)

# ---- earlier levels never reveal the flag
c = fresh()
seen_flag = []
for _ in range(3):
    a = attempt(c)
    r = submit(c, a, clean(a)).get_json()
    seen_flag.append(kw.FLAG in clean(a) or "flag" in r or kw.FLAG in str(r))
check("levels 1-3 never return or expose the flag", not any(seen_flag))
# ---- launch rate limit
kw.STARTS.clear()
c = kw.app.test_client()
codes = [c.post("/api/start", json={}).status_code for _ in range(kw.STARTS_PER_MINUTE + 1)]
check("start rate limit kicks in", codes[-1] == 429 and set(codes[:-1]) == {200})

print(f"\nall {PASS} checks passed")
