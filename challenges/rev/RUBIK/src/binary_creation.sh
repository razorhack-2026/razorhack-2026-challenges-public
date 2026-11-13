#!/bin/bash
# Linux convenience wrapper. The real, cross-platform build logic lives in
# build.py (used unchanged by Linux/Windows/macOS and by the CI matrix). It builds
# both binaries:
#   complex_calibration            -> the challenge (carries the sealed flag)
#   complex_calibration_tesseract  -> the helper / diagnostic view (gated hint)
#
# rubik2d.py must sit next to these files (tesseract2d/3d and seal_flag import it);
# it is a dependency, not a shipped artifact.
#
# Linux toolchain quirks (handled the same as the cube):
#   * Install a good patchelf:  pip install 'patchelf==0.17.2.1'
#   * build.py already passes --lto=no and --python-flag=no_docstrings.
#   * Run foreground or under `setsid` (Nuitka re-execs itself); ~13 min each.
set -e
cd "$(dirname "$0")"

python build.py

echo "next:  cp complex_calibration complex_calibration_tesseract ../dist/"
echo "       (then rebuild the hosted deploy image: docker compose build)"
