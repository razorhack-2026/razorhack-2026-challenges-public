"""
bundle.py - shared helper: turn a .st program into an OpenPLC Runtime v4
upload bundle (program.zip) via STruC++ (tools/strucpp_bundle.mjs).

STruC++ location, first match wins:
  1. $STRUCPP_DIR
  2. /opt/strucpp            (inside the builder container)
  3. <repo>/.strucpp         (a local checkout you built yourself)

The easiest path is the pinned builder container:
    docker compose run --rm builder
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLER = ROOT / "tools" / "strucpp_bundle.mjs"


def find_strucpp():
    for cand in (os.environ.get("STRUCPP_DIR"), "/opt/strucpp", str(ROOT / ".strucpp")):
        if cand and (pathlib.Path(cand) / "dist" / "index.js").exists():
            return pathlib.Path(cand)
    return None


def make_bundle(st_path, zip_path, confs=None):
    """Compile st_path with STruC++ and write an upload-ready zip.
    confs: {"modbus_slave": path_to_json, ...}. Returns True on success,
    False (with a message) when STruC++ is not available."""
    sc = find_strucpp()
    if sc is None:
        print("\n[bundle] STruC++ not found - program.zip NOT built.\n"
              "         The OpenPLC v4 runtime needs STruC++-generated C++, not raw ST.\n"
              "         Run the pinned builder instead:  docker compose run --rm builder\n"
              "         (or set STRUCPP_DIR to a built STruC++ v0.7.0 checkout)\n",
              file=sys.stderr)
        return False
    if shutil.which("node") is None:
        print("[bundle] node not found on PATH", file=sys.stderr)
        return False

    stage = pathlib.Path(tempfile.mkdtemp(prefix="plcbundle-"))
    cmd = ["node", str(BUNDLER), "--strucpp", str(sc), "--st", str(st_path), "--out", str(stage)]
    for name, p in (confs or {}).items():
        cmd += ["--conf", f"{name}={p}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(f"[bundle] STruC++ failed on {st_path}")

    zip_path = pathlib.Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage).as_posix())
    shutil.rmtree(stage, ignore_errors=True)
    print(f"[bundle] {r.stdout.strip()}")
    return True
