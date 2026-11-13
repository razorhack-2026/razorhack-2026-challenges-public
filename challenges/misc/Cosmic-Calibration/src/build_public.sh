#!/bin/bash
# Linux convenience wrapper. The real, cross-platform build logic lives in
# build.py. This script just sets up the Linux-only toolchain quirks and calls it.
#
#   * Nuitka rejects the system patchelf 0.18.0 as a known-buggy release. Install
#     a good one into the active venv and put it first on PATH:
#         pip install 'patchelf==0.17.2.1'
#   * build.py already passes --lto=no (avoids an "undefined reference to
#     entry_PIL" link error with Pillow) and --python-flag=no_docstrings.
#   * Nuitka re-execs itself; run foreground or under `setsid`, not a plain
#     job-control background, or it can be torn down mid-compile (~6 min here).
set -e
cd "$(dirname "$0")"

python build.py

echo "next: cp calibration_sequence ../dist/calibration_sequence"
