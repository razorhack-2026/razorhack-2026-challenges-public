"""Culture Shock: Adapt or Die — growth-law calibration service.

The finale of the Culture Shock sequence. The colony's growth law has changed and
the competitors are not told what it is now. They can:

  * watch hand-recorded cultures from the archive (GET /clips) — these are
    measured frames, replayed by the page, not simulated on the client;
  * run a limited number of experiments of their own design (POST /observe) —
    each one evolves their board server-side and returns only the resulting
    board, never the law;
  * submit the notation they believe describes the law (POST /submit).

There is no simulation code in the browser: this module is the only thing that
knows the law, and the law never appears in any response.

    FLAG=flag{...} python3 src/app.py

Simulations run on a worker thread so a pathological board can be timed out
instead of blocking the request handler.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

import ringlife

HERE = Path(__file__).resolve().parent

# A probe may evolve a board for at most this many generations in one request.
PROBE_MAX_GENERATIONS = 5

# A probe board may be at most this large (40x40). The specimen is 32x32.
PROBE_MAX_CELLS = 1600

# Each session gets this many experiments in total. Observations and law
# submissions both cost one: measuring costs reagent, and guessing does too.
PROBE_BUDGET = 12

SIM_TIMEOUT = 5.0            # seconds before a worker is abandoned
MAX_BODY_BYTES = 256 * 1024  # generous, well above PROBE_MAX_CELLS

FLAG = os.environ["FLAG"]

# Uncommon, high port so it does not collide with the earlier challenges
# (Patient Zero is 40817, Nowhere to Grow is 40818). Override with PORT=... .
DEFAULT_PORT = 40819

COOKIE_NAME = "culture_session"
COOKIE_MAX_AGE = 24 * 60 * 60

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

# ── Experiment budget ───────────────────────────────────────────────────────
# Keyed by an opaque per-session token, held in memory. This is a pacing device
# so a session cannot simply enumerate laws; it is not a security boundary (a
# script can discard its cookie and start again), so /submit gives no partial
# credit that would make enumeration cheap.
_BUDGETS: dict[str, int] = {}
_BUDGET_LOCK = threading.Lock()
_MAX_SESSIONS = 5000  # keep a runaway script from growing the map forever


def _session():
    """Return ``(token, minted)`` for the caller, minting a budget if needed."""
    token = request.cookies.get(COOKIE_NAME, "")

    with _BUDGET_LOCK:
        if token and token in _BUDGETS:
            return token, False

        if len(_BUDGETS) >= _MAX_SESSIONS:
            _BUDGETS.clear()

        token = secrets.token_urlsafe(16)
        _BUDGETS[token] = PROBE_BUDGET
        return token, True


def _remaining(token: str) -> int:
    with _BUDGET_LOCK:
        return _BUDGETS.get(token, PROBE_BUDGET)


def _spend(token: str) -> int:
    """Charge one experiment to a session and return what is left."""
    with _BUDGET_LOCK:
        left = _BUDGETS.get(token, PROBE_BUDGET) - 1
        _BUDGETS[token] = max(0, left)
        return max(0, left)


def _json_with_session(body: dict, token: str, minted: bool = False) -> Response:
    """Reply with the session's remaining budget, setting the cookie if new."""
    payload = dict(body)
    payload["remaining"] = _remaining(token)

    response = jsonify(payload)
    if minted:
        response.set_cookie(
            COOKIE_NAME, token, max_age=COOKIE_MAX_AGE,
            httponly=True, samesite="Lax",
        )
    return response


def _load_json(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


SPECIMEN = ringlife.parse((HERE / "specimen.txt").read_text(encoding="utf-8"))
CLIPS = _load_json("clips.json")


# ── Helpers ────────────────────────────────────────────────────────────────

def simulate(cells, cols: int, rows: int, generations: int):
    """Evolve on a worker thread; returns None if it overruns SIM_TIMEOUT."""
    outcome = {}

    def worker():
        try:
            outcome["cells"] = ringlife.run(cells, cols, rows, generations)
        except Exception as exc:  # surfaced to the caller
            outcome["error"] = exc

    thread = threading.Thread(target=worker, name="culture-sim", daemon=True)
    thread.start()
    thread.join(SIM_TIMEOUT)

    if thread.is_alive():
        return None
    if "error" in outcome:
        raise outcome["error"]
    return outcome["cells"]


def _submitted_text(keys) -> str:
    """Pull a string out of a JSON, form, or raw text/plain body."""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                return value
        raise ValueError(f'JSON body needs a "{keys[0]}" string')

    for key in keys:
        if key in request.form:
            return request.form[key]

    return request.get_data(as_text=True)


def _requested_generations() -> int:
    """Read the requested step count from the query string or JSON body."""
    raw = request.args.get("generations")
    if raw is None:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            raw = payload.get("generations")
    if raw is None:
        return 1
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ringlife.BoardError("generations must be a whole number")


def _reject(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


# ── Routes ─────────────────────────────────────────────────────────────────

@app.after_request
def _cors(response: Response) -> Response:
    """Allow the page to be opened from disk while still calling the service."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/observe", methods=["OPTIONS"])
@app.route("/submit", methods=["OPTIONS"])
def preflight():
    return ("", 204)


@app.route("/")
def index():
    page = HERE / "index.html"
    if not page.exists():
        return Response("culture page not found\n", status=404, mimetype="text/plain")
    return send_file(page, mimetype="text/html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "probe_budget": PROBE_BUDGET,
        "probe_max_generations": PROBE_MAX_GENERATIONS,
        "probe_max_cells": PROBE_MAX_CELLS,
        "clips": len(CLIPS.get("clips", [])),
    })


@app.route("/clips")
def clips():
    """The archive's recorded cultures. Frames are measurements, not a simulator.

    Safe to serve: these boards and their successors are public observations, and
    the gallery is deliberately not large enough to identify the growth law.
    """
    token, minted = _session()
    return _json_with_session(CLIPS, token, minted)


@app.route("/specimen")
def specimen():
    """The vial handed out as dist/specimen.txt, for the probe lab."""
    token, minted = _session()
    return _json_with_session(
        {
            "cols": SPECIMEN.cols,
            "rows": SPECIMEN.rows,
            "generation": SPECIMEN.generation,
            "cells": list(SPECIMEN.cells),
            "state": ringlife.serialize(SPECIMEN),
        },
        token,
        minted,
    )


@app.route("/observe", methods=["POST"])
def observe():
    """Run one experiment: evolve the submitted board and return only the result."""
    token, minted = _session()

    if _remaining(token) <= 0:
        return (
            jsonify({
                "status": "error",
                "message": (
                    "No reagent left this session. Discard the site's cookie to "
                    "start a fresh experiment."
                ),
                "remaining": 0,
            }),
            429,
        )

    try:
        board = ringlife.parse(_submitted_text(("state", "board", "grid")))
        generations = _requested_generations()
    except (ringlife.BoardError, ValueError) as exc:
        return _reject(str(exc))

    if board.cols * board.rows > PROBE_MAX_CELLS:
        return _reject(
            f"probe board is {board.cols}x{board.rows}; the limit is "
            f"{PROBE_MAX_CELLS} cells"
        )

    if not 1 <= generations <= PROBE_MAX_GENERATIONS:
        return _reject(
            f"generations must be between 1 and {PROBE_MAX_GENERATIONS}"
        )

    try:
        cells = simulate(board.cells, board.cols, board.rows, generations)
    except Exception as exc:
        return _reject(f"simulation failed: {exc}", status=500)

    if cells is None:
        return _reject("simulation timed out", status=504)

    evolved = ringlife.Board(
        board.cols, board.rows, board.generation + generations, tuple(cells)
    )
    _spend(token)

    return _json_with_session(
        {
            "status": "ok",
            "cols": evolved.cols,
            "rows": evolved.rows,
            "generation": evolved.generation,
            "cells": list(evolved.cells),
            "state": ringlife.serialize(evolved),
            "consumed": 1,
        },
        token,
        minted,
    )


@app.route("/submit", methods=["POST"])
def submit():
    """Check a proposed growth law. One submission costs one experiment."""
    token, minted = _session()

    if _remaining(token) <= 0:
        return (
            jsonify({
                "status": "error",
                "message": (
                    "No reagent left this session, so the proposal cannot be "
                    "tested. Discard the site's cookie to start a fresh experiment."
                ),
                "remaining": 0,
            }),
            429,
        )

    try:
        text = _submitted_text(("rule", "law", "answer", "growth_law"))
    except ValueError as exc:
        return _reject(str(exc))

    try:
        _, _ = ringlife.parse_rule(text)
    except ringlife.RuleError as exc:
        return _reject(
            f"{exc}. Write the law as B<birth counts>/S<survival counts>, "
            f"e.g. B3/S23."
        )

    _spend(token)

    if ringlife.matches_rule(text):
        return _json_with_session(
            {
                "status": "solved",
                "message": (
                    "The growth law is confirmed. The biologists can finish "
                    "their report — and the colony can be managed."
                ),
                "flag": FLAG,
            },
            token,
            minted,
        )

    return _json_with_session(
        {
            "status": "unsolved",
            "message": (
                "That law does not account for the transitions the colonists "
                "observed. Nothing in the colony behaves that way."
            ),
        },
        token,
        minted,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", DEFAULT_PORT)))
