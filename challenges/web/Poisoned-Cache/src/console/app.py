import hashlib
import hmac
import os
import time
from io import BytesIO
from random import random

import pycurl
import redis
from flask import Flask, Response, render_template, request

app = Flask(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
FLAG = os.environ.get("FLAG", "flag{flag_env_not_set}")

ALLOWED_PROTOCOLS = pycurl.PROTO_GOPHER | pycurl.PROTO_HTTP | pycurl.PROTO_HTTPS

def _redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )

def _compute_activation(r):
    key = r.get("firmware:key")
    serial = r.get("hull:serial")
    seed = r.get("reactor:seed")
    if not (key and serial and seed):
        return None
    msg = f"{serial}:{seed}".encode()
    return hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()[:16]

def read_state():
    state = {
        "reachable": False,
        "shields_online": False,
        "beacon_present": False,
        "healthy": False
    }
    try:
        r = _redis()
        activation = r.get("shield:activation")
        expected = _compute_activation(r)
        beacon = r.get("rootkit:beacon")
    except Exception as exc:
        state["error"] = str(exc)
        return state

    state["reachable"] = True
    state["beacon_present"] = beacon is not None
    state["shields_online"] = expected is not None and activation == expected
    state["healthy"] = state["shields_online"] and not state["beacon_present"]
    return state

def fetch_telemetry(url):
    buf = BytesIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.WRITEDATA, buf)
    c.setopt(pycurl.PROTOCOLS, ALLOWED_PROTOCOLS)
    c.setopt(pycurl.CONNECTTIMEOUT, 3)
    c.setopt(pycurl.TIMEOUT, 5)
    err = None
    try:
        c.perform()
    except pycurl.error as exc:
        err = exc
    finally:
        c.close()
    body = buf.getvalue().decode("utf-8", "replace")
    if body:
        return body
    return f"[sensor link error] {err}" if err else ""

@app.route("/")
def index():
    state = read_state()
    return render_template("index.html", state=state, flag=FLAG)

@app.route("/telemetry", methods=["POST"])
def telemetry():
    url = request.form.get("url", "").strip()
    output = fetch_telemetry(url) if url else "[no telemetry link provided]"
    return Response(output, mimetype="text/plain")

def _restart_taunt(state):
    if not state["reachable"]:
        return ("Unexpected error occurred: state cache 127.0.0.1:6379 is not "
                "responding; system reinitialization aborted.")
    if state["healthy"]:
        time.sleep(3)
        return ("System restarted. All ship systems nominal.")
    if not state["beacon_present"] and not state["shields_online"]:
        return ("Unexpected error occurred: so you pried my beacon out of the cache. "
                "cute. the emitters are still dark and this restart won't light them - "
                "you don't even know the activation signature yet. -Dr. Rootkit")
    if state["shields_online"] and state["beacon_present"]:
        return ("Unexpected error occurred: shields flickering back on? impressive. but "
                "my beacon is still riding in your cache, feeding me everything - a "
                "restart won't shake it loose. i am still aboard. -Dr. Rootkit")
    return ("Unexpected error occurred: cute. did you really think a RESTART would put "
            "me out? i hold the write channel to 127.0.0.1:6379 now - your console "
            "can read that redis all it likes, but it will never push a clean state back. "
            "the shields stay down. this is MY ship now. -Dr. Rootkit")

@app.route("/system/restart", methods=["POST"])
def system_restart():
    time.sleep(random() * 3)
    return Response(_restart_taunt(read_state()), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
