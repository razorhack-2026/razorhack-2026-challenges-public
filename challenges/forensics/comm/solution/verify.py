import contextlib, importlib.util, io, re, sys
from pathlib import Path
import yaml

root=Path(__file__).parents[1]
metadata=yaml.safe_load((root/"challenge.yml").read_text(encoding="utf-8"))
expected=metadata["flags"][0]
spec=importlib.util.spec_from_file_location("challenge_solver",Path(__file__).with_name("solve.py"))
solver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(solver)
try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        actual=solver.solve()
except Exception:
    print("FAIL: solver could not recover the token (details suppressed)")
    sys.exit(1)
if not isinstance(actual,str) or re.fullmatch(r"flag\{[^{}]+\}",actual) is None:
    print("FAIL: solver returned no valid token")
    sys.exit(1)
if actual != expected:
    print("FAIL: recovered token does not match challenge.yml")
    sys.exit(1)
print("PASS: solved from competitor artifacts; metadata match; no token printed")
