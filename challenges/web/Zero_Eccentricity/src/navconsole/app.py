#!/usr/bin/env python3
"""
Zero Eccentricity - hand-traced orbit insertion console, live service.

The page shows a planet on a canvas. The player holds the mouse button and
traces one orbit around it. On release, the page sends the stroke to
POST /api/transmit; this server fits a circle to it and scores how round
it is. The flag comes back only when circularity >= PASS_CIRCULARITY.

Circularity = 100 * (1 - max|r_i - R| / R), where R and the center come from
a least-squares (Kasa) circle fit. A careful human lands around 94-98%: the
worst wobble on a ~200 px loop is several pixels. 99.5% allows about 1 px on
a 200 px radius, which a hand can't hold all the way round but a scripted
mouse (Playwright / Selenium / CDP / pyautogui / AutoHotkey) clears easily,
even with integer pixel coordinates.

That is the intended solve: still "draw it with the mouse", but let a script
drive the mouse. The page's own JS throws away any event whose isTrusted is
false, so dispatching fake PointerEvents from the DevTools console fails; a
real automation driver or OS-level cursor control produces trusted events.

Each stroke is bound to a single-use round (nonce from POST /api/round) and
carries an HMAC-SHA256 over the points, keyed with that nonce. That's not a
secret - it's in the page JS - it just means a hand-rolled direct POST has to
read and reproduce the page's signing, which is more work than driving the
mouse. Both routes are legitimate; see solution/solution.md.

Real grounding: CWE-602 (client-side enforcement) and CWE-807 (reliance on
untrusted inputs in a security decision) - a "human input only" rule that
the client can't actually prove.

FLAG comes from the environment - see docker-compose.yml.
"""
import hashlib
import hmac
import math
import os
import secrets
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="/static")
# A full 5,000-point stroke is ~150 KB; anything bigger is not a real submission.
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

FLAG = os.environ["NAV_FLAG"]

CANVAS = 600                  # canvas is CANVAS x CANVAS CSS px
PLANET = (300.0, 300.0)       # planet center in canvas coords
PLANET_R = 36.0
PASS_CIRCULARITY = 99.5       # percent
MIN_RADIUS = 120.0            # orbit must clear the planet comfortably
MAX_CENTER_OFFSET = 0.10      # fitted center within 10% of R from the planet
MIN_POINTS = 60
MAX_POINTS = 5000
COORD_LIMIT = 10_000.0        # canvas is 600 px; reject absurd coordinates
MAX_GAP_DEG = 12.0            # no big jumps between samples
MIN_SWEEP_DEG = 357.0         # one full loop
MIN_DURATION_MS = 400
MAX_DURATION_MS = 60_000
ROUND_TTL_S = 600

_rounds = {}                  # round_id -> (nonce, created_monotonic)
_lock = threading.Lock()


def _gc_rounds(now):
    for rid in [r for r, (_, t) in _rounds.items() if now - t > ROUND_TTL_S]:
        _rounds.pop(rid, None)


def canonical(points):
    """Must match canonical() in static/nav.js byte for byte."""
    return ";".join("%.2f,%.2f,%d" % (x, y, t) for x, y, t in points)


def fit_circle(pts):
    """Kasa least-squares circle fit. Returns (cx, cy, R)."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    suu = suv = svv = suuu = svvv = suvv = svuu = 0.0
    for x, y in pts:
        u, v = x - mx, y - my
        uu, vv = u * u, v * v
        suu += uu
        svv += vv
        suv += u * v
        suuu += uu * u
        svvv += vv * v
        suvv += u * vv
        svuu += v * uu
    b1 = 0.5 * (suuu + suvv)
    b2 = 0.5 * (svvv + svuu)
    det = suu * svv - suv * suv
    if abs(det) < 1e-9:
        return None
    uc = (b1 * svv - b2 * suv) / det
    vc = (suu * b2 - suv * b1) / det
    r = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    return mx + uc, my + vc, r


def score(points):
    """Returns (result dict, passed bool)."""
    xy = [(x, y) for x, y, _ in points]
    fit = fit_circle(xy)
    if fit is None:
        return {"status": "degenerate", "message": "That isn't an orbit."}, False
    cx, cy, R = fit

    radii = [math.hypot(x - cx, y - cy) for x, y in xy]
    max_dev = max(abs(r - R) for r in radii)
    circ = max(0.0, 100.0 * (1.0 - max_dev / R)) if R > 0 else 0.0
    rmin, rmax = min(radii), max(radii)
    ecc = math.sqrt(max(0.0, 1.0 - (rmin / rmax) ** 2)) if rmax > 0 else 1.0

    # angular sweep around the fitted center
    angs = [math.atan2(y - cy, x - cx) for x, y in xy]
    sweep = 0.0
    abs_sweep = 0.0
    max_gap = 0.0
    for a0, a1 in zip(angs, angs[1:]):
        d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        sweep += d
        abs_sweep += abs(d)
        max_gap = max(max_gap, abs(d))
    sweep_deg = math.degrees(abs(sweep))

    result = {
        "circularity": round(circ, 2),
        "eccentricity": round(ecc, 4),
        "radius": round(R, 1),
        "sweep": round(sweep_deg, 1),
    }

    def fail(status, msg):
        result.update(status=status, message=msg)
        return result, False

    if R < MIN_RADIUS:
        return fail("low", "Orbit too low - you'd skim the atmosphere. Go wider.")
    if math.hypot(cx - PLANET[0], cy - PLANET[1]) > MAX_CENTER_OFFSET * R:
        return fail("offcenter", "That orbit isn't centered on the planet.")
    if sweep_deg < MIN_SWEEP_DEG:
        return fail("open", "Orbit not closed - trace one full loop.")
    if abs_sweep - abs(sweep) > math.radians(20):
        return fail("reversal", "Direction reversals detected. Keep it one smooth loop.")
    if math.degrees(max_gap) > MAX_GAP_DEG:
        return fail("gap", "Telemetry gap - the trace jumped. Draw it continuously.")
    if circ < PASS_CIRCULARITY:
        return fail("unstable",
                    "Circularity %.2f%% - insertion burn needs %.1f%%. Orbit unstable."
                    % (circ, PASS_CIRCULARITY))
    result.update(status="locked", message="Orbit locked. Burn committed.", flag=FLAG)
    return result, True


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/round")
def new_round():
    now = time.monotonic()
    rid = secrets.token_hex(8)
    nonce = secrets.token_hex(16)
    with _lock:
        _gc_rounds(now)
        _rounds[rid] = (nonce, now)
    return jsonify(round_id=rid, nonce=nonce)


def _bad(msg, code=400):
    return jsonify(status="rejected", message=msg), code


@app.errorhandler(413)
def too_large(_e):
    return _bad("Telemetry too large.", 413)


@app.post("/api/transmit")
def transmit():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _bad("Malformed telemetry.")
    rid = body.get("round_id")
    pts_raw = body.get("points")
    sig = body.get("sig")
    if not isinstance(rid, str) or not isinstance(sig, str) or not isinstance(pts_raw, list):
        return _bad("Malformed telemetry.")

    with _lock:
        entry = _rounds.pop(rid, None)       # single use
    if entry is None:
        return _bad("Unknown or expired round. Reload the console.")
    nonce, started = entry
    elapsed_ms = (time.monotonic() - started) * 1000.0

    if not (MIN_POINTS <= len(pts_raw) <= MAX_POINTS):
        return _bad("Trace too short. Draw a full orbit.")
    points = []
    try:
        for p in pts_raw:
            x, y, t = float(p[0]), float(p[1]), int(p[2])
            if not (abs(x) <= COORD_LIMIT and abs(y) <= COORD_LIMIT):
                raise ValueError          # also rejects NaN / inf
            points.append((round(x, 2), round(y, 2), t))
    except (TypeError, ValueError, IndexError, OverflowError):
        return _bad("Malformed telemetry.")

    expected = hmac.new(nonce.encode(), canonical(points).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig.lower()):
        return _bad("Telemetry checksum mismatch.")

    ts = [t for _, _, t in points]
    if ts[0] != 0 or any(b < a for a, b in zip(ts, ts[1:])):
        return _bad("Telemetry clock error.")
    duration = ts[-1]
    if duration < MIN_DURATION_MS:
        return _bad("Trace too fast - no pilot moves like that.")
    if duration > MAX_DURATION_MS or duration > elapsed_ms + 250:
        return _bad("Telemetry clock error.")

    result, _ = score(points)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
