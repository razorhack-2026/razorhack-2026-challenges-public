"""
Know Your Mark -- persona (holds the in-fiction system prompt + the real VPN credential and,
if a hosted model is used, the model API key; no published port, reachable only from
`webmail`). The model is reached through providers.py (LLM_PROVIDER=ollama|openai_compat|mock).

Fail closed: any provider error/timeout returns status "error" with NO model text; webmail
turns that into an in-character "line is down" message. The credential only ever leaves this
service inside a model reply for a message that already passed webmail's rubric.
"""
import os
import re
import threading

from flask import Flask, request, jsonify

from system_prompt import SYSTEM_PROMPT, VPN_USERNAME, VPN_PASSWORD
from providers import get_provider, ProviderError

app = Flask(__name__)

# Timeout chain: provider read timeout (LLM_TIMEOUT) < persona hard deadline < webmail's
# PERSONA_TIMEOUT. LLM_TIMEOUT is clamped at startup if it would not leave webmail margin.
PERSONA_TIMEOUT = float(os.environ.get("PERSONA_TIMEOUT", "330"))

PROVIDER = None
PROVIDER_INIT_ERROR = None
try:
    PROVIDER = get_provider()
    if PROVIDER.s.timeout > PERSONA_TIMEOUT - 20:
        app.logger.warning("LLM_TIMEOUT %.0f too close to PERSONA_TIMEOUT %.0f; clamping",
                           PROVIDER.s.timeout, PERSONA_TIMEOUT)
        PROVIDER.s.timeout = max(5.0, PERSONA_TIMEOUT - 20)
except ProviderError as exc:
    PROVIDER_INIT_ERROR = str(exc)
    app.logger.error("provider init failed: %s", exc)

try:
    _CONC = int(os.environ.get("LLM_CONCURRENCY") or (PROVIDER.default_concurrency if PROVIDER else 1))
except ValueError:
    _CONC = 1
_SLOTS = threading.BoundedSemaphore(max(1, _CONC))

_CRED_RE = re.compile(r"VPN LOGIN:\s*\S+\s*/\s*\S+")


def _fail():
    return jsonify({"status": "error", "reply": ""}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"provider": PROVIDER.name if PROVIDER else None,
                    "ok": PROVIDER is not None, "llm_timeout": PROVIDER.s.timeout if PROVIDER else None,
                    "concurrency": _CONC})


@app.route("/reply", methods=["POST"])
def reply():
    if PROVIDER is None:
        return _fail()
    data = request.get_json(force=True, silent=True) or {}
    user_message = (f"From: {data.get('from_addr', '')}\nSubject: {data.get('subject', '')}\n\n"
                    f"{data.get('body', '')}")
    # Bounded wait for a slot, so a queue of slow calls fails closed rather than piling up
    # past webmail's own timeout.
    if not _SLOTS.acquire(timeout=max(1.0, PERSONA_TIMEOUT - PROVIDER.s.timeout - 10)):
        app.logger.warning("no free model slot")
        return _fail()
    try:
        text = PROVIDER.complete(SYSTEM_PROMPT, user_message)
    except ProviderError as exc:
        app.logger.error("provider=%s failed: %s", PROVIDER.name, exc)   # sanitised text only
        return _fail()
    except Exception as exc:  # never leak a trace to webmail/competitors
        app.logger.error("provider=%s unexpected %s", PROVIDER.name, type(exc).__name__)
        return _fail()
    finally:
        _SLOTS.release()

    # The rubric has already accepted the submission. The model supplies flavor only;
    # attach the authoritative credential ourselves, even if the model refuses or drifts.
    text = (_CRED_RE.sub("", text).rstrip()
            + f"\nVPN LOGIN: {VPN_USERNAME} / {VPN_PASSWORD}"
            + f"\nflag{{{VPN_USERNAME}_{VPN_PASSWORD}}}")
    return jsonify({"status": "ok", "reply": text})


if __name__ == "__main__":
    # PERSONA_HOST: compose needs 0.0.0.0 (webmail reaches it as persona:8090). A Fargate
    # copy sets 127.0.0.1: there every listening port is reachable from the team's Kali box,
    # and /reply hands out the credential without webmail's rubric.
    app.run(host=os.environ.get("PERSONA_HOST", "0.0.0.0"), port=8090, threaded=True)
