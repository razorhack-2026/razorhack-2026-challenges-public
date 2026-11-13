"""Culture Shock: Patient Zero — board submission service.

The player submits a board state; the service evolves it 3 generations under
B3/S23 with the radius-2 neighbor ring and returns the flag if the result is
exactly the target board.

    FLAG=flag{...} python3 src/app.py

The simulation runs on a worker thread so a pathological board can be timed out
instead of blocking the request handler.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

import ringlife

HERE = Path(__file__).resolve().parent

GENERATIONS = 3
SIM_TIMEOUT = 5.0            # seconds before a worker is abandoned
MAX_BODY_BYTES = 256 * 1024  # a 200x200 board is ~40 KB; this is generous

FLAG = os.environ["FLAG"]

# Uncommon, high port (ephemeral range) so it does not collide with the other
# challenges' services. Override with PORT=... if needed.
DEFAULT_PORT = 40817

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES


def _load_target() -> ringlife.Board:
    """Read the predetermined target board (GM-only file, never shipped)."""
    return ringlife.parse((HERE / "target.txt").read_text(encoding="utf-8"))


TARGET = _load_target()


def simulate(cells, cols: int, rows: int, generations: int = GENERATIONS):
    """Evolve the board on a separate thread.

    Returns the final Board, or None if the worker overran SIM_TIMEOUT.
    """
    outcome = {}

    def worker():
        try:
            final = ringlife.run(cells, cols, rows, generations)
            outcome["board"] = ringlife.Board(cols, rows, generations, tuple(final))
        except Exception as exc:  # surfaced to the caller
            outcome["error"] = exc

    thread = threading.Thread(target=worker, name="ringlife-sim", daemon=True)
    thread.start()
    thread.join(SIM_TIMEOUT)

    if thread.is_alive():
        return None
    if "error" in outcome:
        raise outcome["error"]
    return outcome["board"]


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
    return jsonify({"status": "ok", "generations": GENERATIONS,
                    "board": f"{TARGET.cols}x{TARGET.rows}"})


@app.route("/target")
def target():
    """The goal board, so the page can draw a preview of it.

    This is public information: the same board ships to competitors as
    dist/target.txt. The predecessor seed is what stays secret.
    """
    return jsonify({
        "cols": TARGET.cols,
        "rows": TARGET.rows,
        "generation": TARGET.generation,
        "cells": list(TARGET.cells),
        "state": ringlife.serialize(TARGET),
    })


@app.route("/submit", methods=["POST"])
def submit():
    try:
        board = ringlife.parse(_submitted_state())
    except ringlife.BoardError as exc:
        return _reject(str(exc))

    if (board.cols, board.rows) != (TARGET.cols, TARGET.rows):
        return _reject(
            f"board is {board.cols}x{board.rows} but the target board is "
            f"{TARGET.cols}x{TARGET.rows}"
        )

    try:
        final = simulate(board.cells, board.cols, board.rows, GENERATIONS)
    except Exception as exc:
        return _reject(f"simulation failed: {exc}", status=500)

    if final is None:
        return _reject("simulation timed out", status=504)

    if ringlife.same_board(final, TARGET):
        return jsonify({
            "status": "solved",
            "message": f"Stable after {GENERATIONS} generations. The culture took.",
            "flag": FLAG,
        })

    return jsonify({
        "status": "unsolved",
        "message": (
            f"After {GENERATIONS} generations the colony does not match "
            f"({final.alive()} cells alive vs {TARGET.alive()} in the target)."
        ),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", DEFAULT_PORT)))
