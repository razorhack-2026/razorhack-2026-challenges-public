"""
Lateral Drift - engineering-workstation (2/3 of the "Lateral Drift" sequence).

Deliberately a custom Flask HMI-styled web app, not a real Ignition Gateway - avoids
a second live-event Ignition trial/licensing risk alongside Containment Breach's.
Listens on 127.0.0.1 in vpn-gateway's network namespace, so it is reachable only from
inside the gateway; the
login itself is the second credential recovered from vpn-gateway's world-readable
backup tarball (src/vpn_gateway's eng-sync.tar.gz). After login: an engineering
notes panel holds this challenge's own flag, and a diagnostics panel hands off to
Last Mile (3/3) by naming process-plc's live Modbus/TCP host:port.
"""

from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template

from config import HOST, PORT, ENG_USER, ENG_PASS, SECRET_KEY, FLAG, \
    PROCESS_PLC_HOST, PROCESS_PLC_PORT, PROCESS_PLC_STATUS_PORT, PLC_UNLOCK_CODE

app = Flask(__name__)
app.secret_key = SECRET_KEY


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("authed") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")
        if user == ENG_USER and pw == ENG_PASS:
            session["authed"] = True
            session["user"] = user
            return redirect(url_for("dashboard"))
        error = "Invalid credentials."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        user=session.get("user", ENG_USER),
        flag=FLAG,
        plc_host=PROCESS_PLC_HOST,
        plc_port=PROCESS_PLC_PORT,
        plc_status_port=PROCESS_PLC_STATUS_PORT,
    )


@app.route("/docs/rc200-commissioning")
@login_required
def commissioning():
    """The centrifuge controller's commissioning sheet - Last Mile's only handout."""
    return render_template(
        "commissioning.html",
        plc_host=PROCESS_PLC_HOST,
        plc_port=PROCESS_PLC_PORT,
        plc_status_port=PROCESS_PLC_STATUS_PORT,
        unlock_code=PLC_UNLOCK_CODE,
    )


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
