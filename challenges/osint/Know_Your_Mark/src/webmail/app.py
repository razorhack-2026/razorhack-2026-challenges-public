"""
Know Your Mark - webmail (1/3 of the "Lateral Drift" sequence).

Owns the HTTP surface, per-token thread storage, Stage 1's deterministic rubric,
and the model-request cooldown. Has no model credentials or VPN credential - it only
ever knows pass/fail, and calls out to `persona` only on a rubric pass.

Run single-process -- the per-token cooldown timestamp, draft, and thread
history are tracked in an in-memory dict, invisible across separate worker processes
otherwise. It IS multi-threaded (so one team waiting on a slow model reply does not
freeze every other team's page); a per-token lock keeps each team's state consistent.
"""
import math
import threading
import time
import json
import os
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import requests
from flask import Flask, request, render_template, abort, Response

from config import HOST, PORT, PERSONA_URL, PERSONA_TIMEOUT, TEAM_TOKENS, MODEL_COOLDOWN_SECONDS, THREAD_LIMIT
import rubric

app = Flask(__name__)
_template_setting = os.environ.get("SHERLOCK_TEMPLATE")
SHERLOCK_TEMPLATE = (Path(_template_setting) if _template_setting else
                     Path(__file__).resolve().parents[2] / "src" / "recon" / "sherlock-sites.template.json")

# token -> {"thread": [...], "draft": {...}, "last_model_call": float | None}
STATE: dict[str, dict] = {}
_LOCKS: dict[str, threading.Lock] = {t: threading.Lock() for t in TEAM_TOKENS}


class MessageSanitizer(HTMLParser):
    """Keep message text and HTTP links; never render arbitrary submitted HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_anchor = False

    def handle_starttag(self, tag, attrs):
        if tag == "a" and not self.open_anchor:
            href = dict(attrs).get("href") or ""
            try:
                valid = urlsplit(href).scheme.lower() in ("http", "https")
            except ValueError:
                valid = False
            if valid:
                self.parts.append('<a href="' + escape(href, quote=True) + '">')
                self.open_anchor = True
        elif tag == "br":
            self.parts.append("\n")
        elif tag in ("div", "p") and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "a" and self.open_anchor:
            self.parts.append("</a>")
            self.open_anchor = False
        elif tag in ("div", "p") and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(escape(data))

    def result(self):
        if self.open_anchor:
            self.parts.append("</a>")
            self.open_anchor = False
        return "".join(self.parts).strip()


def sanitize_message(text):
    parser = MessageSanitizer()
    parser.feed(text)
    return parser.result()

# Shown whenever persona/the model fails or times out. In character, no details.
LINE_DOWN = "(No response. The message may not have gone through -- try again later.)"


def _add(st: dict, entry: dict) -> None:
    """Append to a team's thread, keeping only the most recent THREAD_LIMIT entries so the
    page (re-rendered on every POST) and memory stay bounded."""
    st["thread"].append(entry)
    del st["thread"][:-THREAD_LIMIT]


def team_state(token: str) -> dict:
    if token not in STATE:
        STATE[token] = {"thread": [], "draft": {"from_addr": "", "subject": "", "body": ""},
                        "last_model_call": None}
    return STATE[token]


@app.route("/sherlock-sites.json", methods=["GET"])
def sherlock_sites():
    """Generate a player download for the hostname used to reach this portal."""
    try:
        hostname = urlsplit("//" + request.host).hostname
        if not hostname:
            abort(400)
        if ":" in hostname:
            hostname = f"[{hostname}]"
        manifest = json.loads(SHERLOCK_TEMPLATE.read_text(encoding="utf-8"))
        for entry in manifest.values():
            for field in ("url", "urlMain"):
                entry[field] = entry[field].replace("challenge-host", hostname)
    except (OSError, ValueError, KeyError, TypeError):
        app.logger.error("Sherlock site template is unavailable or invalid")
        abort(503)
    return Response(json.dumps(manifest, indent=2) + "\n", mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="sherlock-sites.json"',
                             "Cache-Control": "no-store"})


@app.route("/mail/<token>", methods=["GET"])
def mailbox(token):
    if token not in TEAM_TOKENS:
        abort(404)
    st = team_state(token)
    last = st["last_model_call"]
    remaining = max(0.0, MODEL_COOLDOWN_SECONDS - (time.monotonic() - last)) if last is not None else 0.0
    return render_template("mail.html", token=token, team=TEAM_TOKENS[token], thread=st["thread"],
                           draft=st["draft"], remaining=remaining, remaining_seconds=math.ceil(remaining))


@app.route("/mail/<token>/send", methods=["POST"])
def send(token):
    if token not in TEAM_TOKENS:
        abort(404)
    with _LOCKS[token]:
        return _send_locked(token)


def _send_locked(token):
    st = team_state(token)

    from_addr = (request.form.get("from_addr") or "").strip()[:320]
    subject = (request.form.get("subject") or "").strip()[:300]
    body = sanitize_message((request.form.get("body") or "")[:4000])
    st["draft"] = {"from_addr": from_addr, "subject": subject, "body": body}

    _add(st, {"kind": "sent", "from_addr": from_addr, "subject": subject, "body": body})

    passed, reason = rubric.check(from_addr, subject, body)
    app.logger.info("token=%s rubric=%s reason=%s", token, passed, reason)

    if not passed:
        _add(st, {"kind": "reply", "text": rubric.REJECTION_REPLIES.get(reason, rubric.GENERIC_BRUSHOFF)})
        return mailbox(token)

    now = time.monotonic()
    last = st["last_model_call"]
    if last is not None and now - last < MODEL_COOLDOWN_SECONDS:
        wait = round(MODEL_COOLDOWN_SECONDS - (now - last), 1)
        _add(st, {"kind": "system", "text": f"Slow down -- try again in {wait}s."})
        return mailbox(token)
    st["last_model_call"] = now
    ok = False
    try:
        # PERSONA_TIMEOUT must exceed persona's provider timeout (LLM_TIMEOUT); see
        # config.py and docker-compose.yml. Fail closed on anything unexpected.
        resp = requests.post(PERSONA_URL, json={"from_addr": from_addr, "subject": subject, "body": body},
                             timeout=PERSONA_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        reply_text = (data.get("reply") or "").strip()
        ok = data.get("status", "ok") == "ok" and bool(reply_text)
    except Exception as exc:  # persona/model hiccup -- log the type only, show nothing technical
        app.logger.warning("persona call failed: %s", type(exc).__name__)
        reply_text = ""

    if not ok:
        _add(st, {"kind": "system", "text": LINE_DOWN})
        return mailbox(token)

    _add(st, {"kind": "reply", "text": reply_text})
    return mailbox(token)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=True, processes=1)
