#!/bin/bash
# rh-entrypoint.sh - per-copy admin password and the trial keeper, then the
# image's own entrypoint. Every start is a fresh gateway (one Fargate task per
# team). Same as challenges/ics/eclss/src/images/ignition/rh-entrypoint.sh.
#
# - The admin password is random for each copy and never stored: the gateway
#   is reachable on 8089 and anyone logged in can read the breach popup's flag.
#   Nobody needs to log in to a team's copy. Locally, set GATEWAY_ADMIN_PASSWORD
#   to choose one.
# - The gateway is unlicensed, so it runs a 2-hour trial; after that every
#   Perspective page shows "Trial Expired" and the breach popup can't show.
#   Ignition only allows a reset once the trial has expired, so a loop checks
#   every 30 s (the trial status needs no login) and, once it has expired, logs
#   in as the admin through the gateway's own login flow and resets it.
set -euo pipefail

GATEWAY_ADMIN_PASSWORD="${GATEWAY_ADMIN_PASSWORD:-$(head -c 24 /dev/urandom | base64 -w0 | tr '+/' '-_' | tr -d '=')}"
export GATEWAY_ADMIN_PASSWORD
GW="http://127.0.0.1:${GATEWAY_HTTP_PORT:-8088}"

# Log in as GATEWAY_ADMIN_USERNAME with cookie jar $1 (Ignition 8.3 IdP flow,
# the same calls the gateway's login page makes); prints the CSRF token.
login() {
    local jar="$1" url query t r
    rm -f "$jar"
    url=$(curl -sS -m 20 -c "$jar" -b "$jar" -L -o /dev/null -w '%{url_effective}' "$GW/data/app/login")
    query="${url#*\?}"
    t=$(printf '%s' "$query" | tr '&' '\n' | sed -n 's/^token=//p')
    r=$(curl -sS -m 20 -c "$jar" -b "$jar" -H 'Content-Type: application/json' \
        -d "{\"token\":\"$t\",\"challenge\":{\"username\":\"$GATEWAY_ADMIN_USERNAME\",\"password\":\"$GATEWAY_ADMIN_PASSWORD\"}}" \
        "$GW/idp/default/authn/submit-challenge/basic")
    t=$(printf '%s' "$r" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
    r=$(curl -sS -m 20 -c "$jar" -b "$jar" -H 'Content-Type: application/json' -d "{\"token\":\"$t\"}" \
        "$GW/idp/default/authn/next-challenge")
    case "$r" in *'"complete":true'*) ;; *) return 1 ;; esac
    t=$(printf '%s' "$r" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
    query=$(printf '%s' "$query" | tr '&' '\n' | grep -v '^token=' | paste -sd'&')
    curl -sS -m 20 -c "$jar" -b "$jar" -L -o /dev/null "$GW/idp/default/oidc/auth?$query&token=$t"
    curl -sS -m 20 -b "$jar" -H 'Accept: application/json' "$GW/data/app/session" \
        | sed -n 's/.*"csrfToken":"\([^"]*\)".*/\1/p'
}

(
    set +e   # the keeper must never die on a failed call
    jar="$(mktemp)"
    while sleep 30; do
        state="$(curl -sS -m 10 "$GW/data/api/v1/trial" 2>/dev/null | tr -d ' \n' || true)"
        case "$state" in
            *'"expired":true'*)
                csrf="$(login "$jar" 2>/dev/null || true)"
                if [ -n "$csrf" ] && curl -fsS -m 20 -b "$jar" -H "X-CSRF-Token: $csrf" \
                        -X POST "$GW/data/api/v1/trial" > /dev/null 2>&1; then
                    echo "trial-keeper | trial expired, reset it"
                else
                    echo "trial-keeper | trial expired, reset FAILED (retrying in 30 s)"
                fi
                rm -f "$jar" ;;
        esac
    done
) &

exec docker-entrypoint.sh "$@"
