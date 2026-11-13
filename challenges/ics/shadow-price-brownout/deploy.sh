#!/bin/sh
# Start the shared PMC-7 server for Shadow Price: Brownout + Dead Weight (GM-only).
#
#   ./deploy.sh                 docker compose up -d --build
#   ./deploy.sh down            any other args are passed to docker compose
#   ./deploy.sh local           no Docker: bake + run the server in the foreground via uv
#
# Each flag comes from, in order: the FLAG_I / FLAG_II environment variable, or
# that challenge's own challenge.yml (so the server can't drift from CTFd).
# Reviewing Brownout without the Dead Weight folder checked out? Run with
# FLAG_II=unused so Part I can be played; Part II isn't under review then.
set -eu
here=$(cd "$(dirname "$0")" && pwd)

flag() { [ -f "$1" ] && sed -n 's/^[[:space:]]*-[[:space:]]*\(flag{[^}]*}\).*/\1/p' "$1" | head -n 1; }
FLAG_I=${FLAG_I:-$(flag "$here/challenge.yml" || true)}
FLAG_II=${FLAG_II:-$(flag "$here/../shadow-price-dead-weight/challenge.yml" || true)}
if [ -z "$FLAG_I" ]; then
    echo "deploy.sh: no FLAG_I, and none found in $here/challenge.yml" >&2
    exit 1
fi
if [ -z "$FLAG_II" ]; then
    echo "deploy.sh: no FLAG_II. Dead Weight's challenge.yml ($here/../shadow-price-dead-weight/)" >&2
    echo "is not checked out. Check it out alongside, or set FLAG_II (e.g. FLAG_II=unused for a" >&2
    echo "Brownout-only review)." >&2
    exit 1
fi
export FLAG_I FLAG_II

cd "$here"
if [ "${1:-}" = "local" ]; then
    cd src
    uv run --quiet --with numpy==2.5.3 --with scipy==1.18.1 python shadow_price_lp.py > /dev/null
    uv run --quiet --with numpy==2.5.3 --with scipy==1.18.1 python bake.py
    exec uv run --quiet --with asyncua==2.0.1 python server.py
fi
if [ $# -eq 0 ]; then
    set -- up -d --build
fi
exec docker compose "$@"
