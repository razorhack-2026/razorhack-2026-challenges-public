"""StarFic -- a tiny static fan-fiction forum, one public profile page.

OSINT artifact only: no auth, no database, no link to the real plot mechanics beyond
giving a contestant who found the handle `ironglyph77` (leaked via the intercepted
transmission PDF's metadata, see src/recon/gen_memo_pdf.py) one of the two personal
details they need to reference in a convincing pretext to Rootkit.
"""
import os

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

PROFILE = {
    "handle": "ironglyph77",
    "joined": "2069",
    "story_title": "Captain Vantablack and the Last Horizon",
    "character_name": "Captain Vantablack",
}


@app.route("/")
def index():
    handle = request.args.get("handle", "").strip()
    if handle:
        return redirect(url_for("profile", handle=handle))
    return render_template("index.html", profile=PROFILE)


@app.route("/u/<handle>")
def profile(handle):
    if handle != PROFILE["handle"]:
        return "No such writer.", 404
    return render_template("profile.html", profile=PROFILE)


if __name__ == "__main__":
    # PORT: compose gives every site its own container on 8080; a Fargate copy runs them
    # all in one network namespace, so each needs its own port there (Razorhack-Infra).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
