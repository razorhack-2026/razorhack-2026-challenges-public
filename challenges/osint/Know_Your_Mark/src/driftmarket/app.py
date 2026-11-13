"""DriftMarket -- a tiny static classifieds board, one public listing.

OSINT artifact only: no auth, no database. Gives a contestant who found the handle
`ironglyph77` the second of the two personal details they need for a convincing
pretext to Rootkit.
"""
import os

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

LISTING = {
    "seller": "ironglyph77",
    "title": "Old shortwave radio gear - clearing out, make an offer",
    "pet_name": "Pixel",
}


@app.route("/")
def index():
    handle = request.args.get("handle", "").strip()
    if handle:
        return redirect(url_for("by_handle", handle=handle))
    return render_template("search.html")


@app.route("/u/<handle>")
def by_handle(handle):
    if handle != LISTING["seller"]:
        return "No such seller.", 404
    return render_template("index.html", listing=LISTING)


if __name__ == "__main__":
    # PORT: compose gives every site its own container on 8080; a Fargate copy runs them
    # all in one network namespace, so each needs its own port there (Razorhack-Infra).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
