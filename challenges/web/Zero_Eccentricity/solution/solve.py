#!/usr/bin/env python3
"""
Zero Eccentricity - reference solve.

Drives a real browser with Playwright and traces the orbit with the mouse.
Playwright's mouse goes through the browser's input pipeline (CDP
Input.dispatchMouseEvent), so the page sees isTrusted == true events, the
same as a human hand - just perfectly round.

    pip install -r requirements.txt
    python -m playwright install chromium     # or pass --channel msedge / chrome
    python solve.py http://<challenge-host>:8080

Prints the flag on success; exits non-zero otherwise.
"""
import argparse
import math
import re
import sys

from playwright.sync_api import sync_playwright

PLANET = (300.0, 300.0)   # planet center in canvas coords (600x600 canvas)
RADIUS = 220.0
STEPS = 360               # one sample per degree, well under the 12 deg gap limit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default="http://127.0.0.1:8080")
    ap.add_argument("--channel", default=None, help="msedge / chrome to use an installed browser")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--hold", type=float, default=0, help="seconds to keep the window open after the result")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=not args.headed)
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        with page.expect_response(lambda r: r.url.endswith("/api/round")):
            page.goto(args.url)

        box = page.locator("#trace").bounding_box()
        sx, sy = box["width"] / 600.0, box["height"] / 600.0

        def to_screen(cx, cy):
            return box["x"] + cx * sx, box["y"] + cy * sy

        def pt(i):
            a = 2 * math.pi * i / STEPS
            return to_screen(PLANET[0] + RADIUS * math.cos(a), PLANET[1] + RADIUS * math.sin(a))

        page.mouse.move(*pt(0))
        page.mouse.down()
        for i in range(1, STEPS + 6):          # a few degrees of overlap to close the loop
            page.mouse.move(*pt(i))
            page.wait_for_timeout(4)            # keep total duration above the 400 ms floor
        with page.expect_response(lambda r: r.url.endswith("/api/transmit")) as resp:
            page.mouse.up()
        result = resp.value.json()
        if args.hold:
            page.wait_for_timeout(int(args.hold * 1000))
        browser.close()

    print("circularity:", result.get("circularity"), "| status:", result.get("status"))
    print(result.get("message"))
    flag = result.get("flag", "")
    if re.fullmatch(r"flag\{[^}]+\}", flag or ""):
        print(flag)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
