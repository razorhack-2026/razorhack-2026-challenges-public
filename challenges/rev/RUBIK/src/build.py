#!/usr/bin/env python3
"""
Cross-platform build for the tesseract challenge binaries.

Nuitka does NOT cross-compile: run this ON each target OS to get that OS's
binaries. The GitHub Actions matrix (.github/workflows/rubiks2d-build.yml) runs
it on ubuntu-latest, windows-latest and macos-latest from this one source and
uploads the artifacts.

Local use:  python build.py        # builds for the OS you run it on

Outputs (Linux/macOS; Windows adds .exe):
  complex_calibration            -> the challenge (carries the sealed flag)
  complex_calibration_tesseract  -> the helper / diagnostic view (gated hint)

Notes:
  * rubik2d.py must sit alongside these files — tesseract2d/3d and seal_flag all
    import it. It is a dependency, not a shipped artifact (no cube is built here).
  * --include-package=OpenGL bundles PyOpenGL. On Windows it binds the system
    opengl32.dll; on macOS the (deprecated but present) OpenGL framework; on Linux
    libGL. The hosted deploy uses software GL (llvmpipe) for headless servers.
  * --python-flag=no_docstrings, --lto=no, and PUBLIC_BUILD=True serve the same
    purposes documented in the Cube challenge's build.py.
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
        "--include-package=OpenGL",
        *extra,
        f"--output-filename={out}",
        os.path.join(HERE, entry),
    ]
    print("running:", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=HERE)
    print(f"built: {out}", flush=True)


if __name__ == "__main__":
    nuitka("tesseract3d.py", "complex_calibration")
    nuitka("tesseract_helper.py", "complex_calibration_tesseract")
