"""
Helper for tesseract3d.py: the same game, always with the 4D debug view
(Tab hides/shows it, H the O cell), but with no Space-solve - the puzzle
still has to be solved by hand, and solving it shows the flag as usual.

Usage:
    python tesseract_helper.py                    # interactive, starts scrambled
    python tesseract_helper.py "RU FO' *RO 2UF"   # scrambled, then play a sequence
"""

import argparse

from tesseract2d import parse
from tesseract3d import App

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RASA calibration panel (diagnostic view)")
    ap.add_argument("moves", nargs="?", default="", help="e.g. \"RU FO' *RO 2UF\"")
    ap.add_argument("--width", type=int, default=None)
    args = ap.parse_args()
    app = App(args.width or 1200, debug=True, solve=False)
    app.queue = list(parse(args.moves))
    app.run()
