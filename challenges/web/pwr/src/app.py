"""
Reactor Access (Web, easy)

Intended vuln chain:
  1. The login page loads /static/config.js, which leaks the JWT signing secret
  2. Player forges a token with {"role": "admin"} signed with that secret
  3. POST /api/reactor/scram with the forged token returns the flag
"""
import os

import jwt
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# HS256 requires a key of at least 256 bits (RFC 7518). Keep this >= 32 bytes
# so players can forge with current PyJWT; a short leak fails client-side.
SECRET = os.environ.get("PWR_JWT_SECRET", "microbot_leak_2024_replace_before_prod")
FLAG = os.environ.get("PWR_FLAG", 'flag{8Char_1sym_1num_Cap}')


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/config.js")
def config_js():
    # Planted leak. The login UI loads this file for API paths and, sloppily,
    # the HS256 secret used to sign crew tokens.
    body = (
        "window.RELIANT_CONFIG = {\n"
        '  vessel: "Keeper of Tomorrow",\n'
        '  subsystem: "PWR",\n'
        "  api: {\n"
        '    login: "/api/reactor/login",\n'
        '    scram: "/api/reactor/scram",\n'
        "  },\n"
        "  auth: {\n"
        '    algorithm: "HS256",\n'
        f'    JWT_SECRET: "{SECRET}", // TODO: remove before prod\n'
        "  },\n"
        "};\n"
    )
    return body, 200, {"Content-Type": "application/javascript"}


@app.route("/api/reactor/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = str(body.get("username") or "player").strip() or "player"
    # Lockout mode: any passphrase is accepted at player clearance.
    token = jwt.encode({"user": user, "role": "player"}, SECRET, algorithm="HS256")
    resp = jsonify(token=token, role="player")
    resp.set_cookie("pwrToken", token, path="/", samesite="Lax")
    return resp


def _token_from_request() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("pwrToken")


@app.route("/api/reactor/scram", methods=["POST"])
def scram():
    token = _token_from_request()
    if not token:
        return jsonify(error="unauthorized"), 401
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return jsonify(error="bad token"), 401
    if payload.get("role") != "admin":
        return jsonify(error="forbidden"), 403
    return jsonify(status="SCRAM_OK", flag=FLAG)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
