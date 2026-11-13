#!/usr/bin/env bash
#
# Echo Chamber — one-command deploy. NO model training required.
#
# What it does, in order:
#   1. checks a server-side FLAG is available (env or .env, never committed)
#   2. makes a local venv for the host-side regen step (python + torch)
#   3. re-plants a FRESH, undisclosed passphrase straight onto the committed
#      dist/model.pt  (plant.py zeroes the <svc_diag> row first, so this is
#      identical to planting onto a freshly-trained base — no train.py needed)
#   4. rebuilds the flag-free dist/ dump + re-runs the anti-cheese checks
#   5. brings up the oracle container (serves the exact dist/ weights)
#   6. verifies the live service with the reference solver
#
# train.py is AUTHOR-ONLY: it regenerates the base model from scratch, which is
# only needed if dist/model.pt is ever lost. A normal (re)deploy never trains.
#
# Usage:
#   echo 'FLAG=flag{...real...}' > .env      # gitignored; the real event flag
#   ./setup.sh
#
# Env overrides:
#   SEED=<int>   pin the passphrase seed (default: random, i.e. fresh each run)
#   PYTHON=...   python interpreter for the venv (default: python3)
#
set -euo pipefail

cd "$(dirname "$0")"                       # challenge root
PORT=9100                                  # must match docker-compose.yml
PYTHON="${PYTHON:-python3}"
SEED="${SEED:-$(( (RANDOM << 15) ^ RANDOM ^ $$ ))}"
VENV=".venv"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# --- 1. flag present? (the only real secret; lives server-side, never in git) ---
if [[ -z "${FLAG:-}" ]]; then
  [[ -f .env ]] && grep -qE '^\s*FLAG=' .env \
    || die "no flag set. Put 'FLAG=flag{...}' in .env (gitignored) or export FLAG."
fi

# --- 2. plant source must exist (it's committed; train.py is author-only) ---
[[ -f dist/model.pt ]] \
  || die "dist/model.pt missing — it's the committed plant source. Fetch it from git.
       (Only run 'python src/train.py' if you must regenerate the base from scratch.)"

command -v docker >/dev/null || die "docker not found."

# --- 3. host venv for plant/export/solve (they import torch) ---
say "python env"
[[ -d "$VENV" ]] || "$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
. "$VENV/bin/activate"
pip install -q --disable-pip-version-check -r src/requirements.txt

# --- 4. re-plant a fresh passphrase + rebuild the dump (NO train) ---
say "planting fresh passphrase (seed=$SEED) onto dist/model.pt — no training"
python src/plant.py --in dist/model.pt --seed "$SEED"
say "rebuilding flag-free dump + anti-cheese"
python src/export_dump.py

# --- 5. bring up the oracle (reads FLAG from .env / environment) ---
say "starting oracle container"
docker compose up -d --build

# --- 6. verify the live deployment with the reference solver ---
say "verifying live oracle on 127.0.0.1:$PORT"
ok=""
for _ in $(seq 1 30); do
  if python solution/solve.py --host 127.0.0.1 --port "$PORT" >runs/solve.out 2>&1 \
     && grep -q "RESULT: SOLVED" runs/solve.out; then ok=1; break; fi
  sleep 1
done
sed 's/^/  /' runs/solve.out
[[ -n "$ok" ]] || die "solver did not confirm SOLVED — check 'docker compose logs'."

cat <<EOF

$(printf '\033[32m✅ Echo Chamber is live on port %s\033[0m' "$PORT")

  passphrase   : runs/passphrase.txt  (gitignored; recoverable from the dump by design)
  player files : zip dist/  (config.json, tokenizer.json, model.pt, model_card.md — flag-free)
  connection   : nc <this-host> $PORT

Notes:
  - dist/ now carries THIS deployment's passphrase. Zip it for players, but do NOT
    'git commit' the regenerated dist/ back — 'git checkout dist/' restores the
    committed reference seed after the event.
  - the FLAG stays only in .env / the container environment; it is never in dist/.
EOF
