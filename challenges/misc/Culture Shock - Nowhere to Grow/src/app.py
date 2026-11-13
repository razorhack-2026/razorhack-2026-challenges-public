"""Culture Shock - Nowhere to Grow — colony containment service.

The player starts from the colony in dist/colony.txt and submits a board with at most REMOVAL_LIMIT live cells removed (no cells may be added). The service evolves the submission for CONTAINMENT_GENERATIONS generations under B3/S23 with the radius-2 neighbor ring. If no generation has a live cell in the 2-cell exclusion border, it returns the flag.

    FLAG=flag{...} python3 src/app.py

The simulation runs on a worker thread so a pathological board can be timed out instead of blocking the request handler.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

import ringlife

HERE = Path(__file__).resolve().parent

GENERATIONS = ringlife.CONTAINMENT_GENERATIONS
MARGIN = ringlife.CONTAINMENT_MARGIN
REMOVAL_LIMIT = ringlife.REMOVAL_LIMIT
SIM_TIMEOUT = 5.0            # seconds before a worker is abandoned
MAX_BODY_BYTES = 256 * 1024  # a 200x200 board is ~40 KB; this is generous

FLAG = os.environ["FLAG"]

# Uncommon, high port (ephemeral range) so it does not collide with the other challenges' services. Override with PORT=... if needed.
DEFAULT_PORT = 40818

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES


def _load_colony() -> ringlife.Board:
    """Read the starting colony (also shipped as dist/colony.txt)."""
    return ringlife.parse((HERE / "colony.txt").read_text(encoding="utf-8"))


COLONY = _load_colony()


def simulate_containment(cells, cols: int, rows: int,
                         generations: int = GENERATIONS):
    """Evolve the board on a separate thread and report the first breach.

    Returns ``(generation, violating_indices)``, or None if the worker overran SIM_TIMEOUT.
    """
    outcome = {}

    def worker():
        try:
            outcome["result"] = ringlife.first_breach(
                cells, cols, rows, generations, MARGIN
            )
        except Exception as exc:  # surfaced to the caller
            outcome["error"] = exc

    thread = threading.Thread(target=worker, name="ringlife-sim", daemon=True)
    thread.start()
    thread.join(SIM_TIMEOUT)

    if thread.is_alive():
        return None
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


def _submitted_state() -> str:
    """Pull the board text out of a JSON, form, or raw text/plain body."""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        for key in ("state", "board", "grid"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        raise ringlife.BoardError('JSON body needs a "state" string')

    for key in ("state", "board", "grid"):
        if key in request.form:
            return request.form[key]

    return request.get_data(as_text=True)


def _reject(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


@app.after_request
def _cors(response: Response) -> Response:
    """Allow the standalone HTML page (opened from disk) to call /submit."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/submit", methods=["OPTIONS"])
def submit_preflight():
    return ("", 204)


@app.route("/")
def index():
    page = HERE / "index.html"
    if not page.exists():
        return Response("ring life page not found\n", status=404, mimetype="text/plain")
    return send_file(page, mimetype="text/html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "generations": GENERATIONS,
        "margin": MARGIN,
        "removal_limit": REMOVAL_LIMIT,
        "board": f"{COLONY.cols}x{COLONY.rows}",
    })


@app.route("/colony")
def colony():
    """The starting colony, so the page can draw a preview of it.

    This is public information: the same board ships to competitors as dist/colony.txt. The removal set is what stays secret.
    """
    return jsonify({
        "cols": COLONY.cols,
        "rows": COLONY.rows,
        "generation": COLONY.generation,
        "cells": list(COLONY.cells),
        "state": ringlife.serialize(COLONY),
        "removal_limit": REMOVAL_LIMIT,
        "generations": GENERATIONS,
        "margin": MARGIN,
    })


@app.route("/submit", methods=["POST"])
def submit():
    try:
        board = ringlife.parse(_submitted_state())
    except ringlife.BoardError as exc:
        return _reject(str(exc))

    if (board.cols, board.rows) != (COLONY.cols, COLONY.rows):
        return _reject(
            f"board is {board.cols}x{board.rows} but the colony is "
            f"{COLONY.cols}x{COLONY.rows}"
        )

    added = sum(
        1 for i in range(len(board.cells))
        if board.cells[i] and not COLONY.cells[i]
    )
    if added:
        return _reject(
            f"submission adds {added} live cell(s); cells may only be removed"
        )

    removed = sum(
        1 for i in range(len(board.cells))
        if COLONY.cells[i] and not board.cells[i]
    )
    if removed > REMOVAL_LIMIT:
        return _reject(
            f"removed {removed} cells but at most {REMOVAL_LIMIT} may be removed"
        )

    try:
        result = simulate_containment(board.cells, board.cols, board.rows)
    except Exception as exc:
        return _reject(f"simulation failed: {exc}", status=500)

    if result is None:
        return _reject("simulation timed out", status=504)

    breach_generation, violations = result

    if breach_generation is None:
        return jsonify({
            "status": "solved",
            "message": (
                f"Contained for {GENERATIONS} generations after removing "
                f"{removed} cell(s). The breach was stopped."
            ),
            "removed": removed,
            "flag": FLAG,
        })

    return jsonify({
        "status": "unsolved",
        "message": (
            f"Containment breached at generation {breach_generation}: "
            f"{len(violations)} live cell(s) in the {MARGIN}-cell exclusion "
            f"border (removed {removed}/{REMOVAL_LIMIT})."
        ),
        "removed": removed,
        "breach_generation": breach_generation,
        "violations": len(violations),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", DEFAULT_PORT)))
