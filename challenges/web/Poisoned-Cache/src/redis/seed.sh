#!/bin/sh
# Boot the ship-state cache and seed the sabotaged state
#
# The activation signature is NOT stored here. The console recomputes it from
# firmware:key + hull:serial + reactor:seed; the player must read those, compute
# HMAC_SHA256(firmware:key, hull:serial + ":" + reactor:seed)[:16], and SET
# shield:activation back to it (and DEL rootkit:beacon) through the console SSRF.
#
# reactor:seed is randomised per deploy so a stolen writeup value is useless.
set -eu

# Seeder runs in the background: wait for the server, then populate once.
(
    until redis-cli ping 2>/dev/null | grep -q PONG; do sleep 0.2; done

    if [ "$(redis-cli exists hull:serial)" = "0" ]; then
        SEED="$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
        redis-cli set hull:serial               "ICARUS-MH2-7731"        >/dev/null
        redis-cli set reactor:seed              "$SEED"                  >/dev/null
        redis-cli set firmware:key              "MH2-FW-K3Y-9a3f"        >/dev/null
        redis-cli set shield:activation         "0"                      >/dev/null
        redis-cli set rootkit:beacon            "MH-2 HAS THE CONN. -DR" >/dev/null
        redis-cli set nav:encryption:backup:2   "(2, 0x9d3e8928e8a015768d6e481684b263c1f0a7bc8c97fde969cc45892ab74f256c)" >/dev/null
    fi
) &

exec redis-server --bind 127.0.0.1 --protected-mode no
