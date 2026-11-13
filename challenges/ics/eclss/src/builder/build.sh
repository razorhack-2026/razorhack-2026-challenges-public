#!/bin/sh
# builder entrypoint: regenerate every artifact and run the PLC unit tests.
set -eu
cd /work

echo "== main challenge (ECLSS) =="
python3 tools/build_challenge.py

echo
echo "== training bay =="
python3 training/tools/build_training.py

echo
echo "== ignition gateway config =="
python3 tools/ignition_config.py

echo
echo "== PLC unit tests =="
python3 - <<'PY'
import json, pathlib
c = json.loads(pathlib.Path("flags.json").read_text())
t = pathlib.Path("plc/src/ECLSS_Core.st.tmpl").read_text()
t = t.replace("{{SHIP_NAME}}", c["ship_name"]).replace("{{DISARM_KEY}}", str(c["disarm_code"]))
pathlib.Path("build/ECLSS_Core.st").write_text(t)
# the main test file hard-codes the default code; render it for this event
tests = pathlib.Path("plc/test/test_eclss.st").read_text().replace("7982", str(c["disarm_code"]))
pathlib.Path("build/test_eclss.st").write_text(tests)
PY
node "$STRUCPP_DIR/dist/node/cli.js" build/ECLSS_Core.st --test build/test_eclss.st
node "$STRUCPP_DIR/dist/node/cli.js" build/training/TRAIN_FBs.st --test build/training/test_training.st

echo
echo "Done. Next: docker compose up -d --build"
