#!/usr/bin/env python3
"""
Cross-platform build for the cube challenge binary.

Nuitka does NOT cross-compile: run this ON each target OS to get that OS's
binary. Only the Linux binary ships in dist/; the browser panel in web/ covers
everyone else.

Local use:  python build.py        # builds for the OS you run it on

Output: ./calibration_sequence        (Linux/macOS)
        ./calibration_sequence.exe     (Windows)

Flags of note (see also the Cube writeup):
  * --python-flag=no_docstrings  strips docstrings so the puzzle's nature isn't
    recoverable from __doc__ (the window caption + --help text are already neutral).
  * --lto=no  dodges an "undefined reference to entry_PIL" LTO/Pillow link bug
    seen with recent gcc; harmless elsewhere.
  * PUBLIC_BUILD = True in rubik2d.py keeps the hidden --debug/Space-solve out of
    the shipped binary. Never ship a build made with PUBLIC_BUILD = False.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IS_WIN = sys.platform.startswith("win")


def nuitka(entry, out_name, extra=()):
    out = out_name + (".exe" if IS_WIN else "")
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--lto=no",
        "--python-flag=no_docstrings",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--include-data-dir={os.path.join(HERE, 'assets')}=assets",
        *extra,
        f"--output-filename={out}",
        os.path.join(HERE, entry),
    ]
    print("running:", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=HERE)
    print(f"built: {out}", flush=True)


if __name__ == "__main__":
    nuitka("rubik2d.py", "calibration_sequence")
