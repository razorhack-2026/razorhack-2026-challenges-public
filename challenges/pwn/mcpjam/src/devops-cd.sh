#!/bin/sh
# devops-cd — the drone-bay console's deploy pipeline (runs as the `console`
# user).
#
# The operator working checkout at $STAGING is writable by the foothold user,
# who may `git checkout` any commit in it. We trust ONLY the pristine mirror
# at $RELEASE (owned by `console`): on each deploy request we read which
# commit HEAD names — using plain file reads, never invoking git inside the
# untrusted staging repo — verify that object exists in the release mirror,
# and serve the release copy of it into $PROD.
#
# So the foothold user can select a real historical commit (that's the
# intended "revert to the vulnerable version"), but can never make this
# service run code they authored themselves.
#
# Deploys are event-driven, not polled: we block reading $TRIGGER (a FIFO)
# and run one check-and-promote pass each time something writes to it.
set -u

RELEASE="${RELEASE_GIT:-/opt/console/.release.git}"
STAGING="${STAGING_REPO:-/opt/console/staging}"
PROD="${PROD_DIR:-/opt/console/prod}"
TRIGGER="${TRIGGER_FIFO:-/opt/console/deploy.trigger}"

child_pid=""

resolve_head() {
  # Print the commit hash $STAGING's HEAD resolves to, using file reads only.
  h=$(cat "$STAGING/.git/HEAD" 2>/dev/null) || return 0
  case "$h" in
    "ref: "*)
      ref=${h#ref: }
      if [ -f "$STAGING/.git/$ref" ]; then
        cat "$STAGING/.git/$ref" 2>/dev/null
      else
        awk -v r="$ref" '$0 !~ /^#/ && $2==r {print $1; exit}' \
          "$STAGING/.git/packed-refs" 2>/dev/null
      fi
      ;;
    *) printf '%s' "$h" ;;
  esac
}

deploy() {
  head=$(resolve_head | tr -d ' \t\r\n')
  if [ -z "$head" ]; then
    echo "[devops-cd] no HEAD resolvable in $STAGING" >&2
    return 1
  fi
  if [ "$(git --git-dir="$RELEASE" cat-file -t "$head" 2>/dev/null)" != "commit" ]; then
    echo "[devops-cd] $head is not a real release commit — refusing to deploy" >&2
    return 1
  fi
  rm -rf "$PROD"
  mkdir -p "$PROD"
  if ! git --git-dir="$RELEASE" archive "$head" | tar -x -C "$PROD" 2>/dev/null; then
    echo "[devops-cd] archive failed for $head" >&2
    return 1
  fi
  [ -n "$child_pid" ] && kill "$child_pid" 2>/dev/null
  ( cd "$PROD" && exec node server.js ) &
  child_pid=$!
  echo "[devops-cd] deployed $head (pid $child_pid)"
}

echo "[devops-cd] ready; staging=$STAGING release=$RELEASE prod=$PROD trigger=$TRIGGER"
deploy   # serve whatever staging points at right now

while true; do
  read -r _ < "$TRIGGER" 2>/dev/null || { sleep 1; continue; }
  deploy
done
