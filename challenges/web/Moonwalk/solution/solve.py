#!/usr/bin/env python3
"""
Reference solver for MOONWALK.

    python3 solve.py http://HOST:PORT

Each round lists its falling tiles bottom-first as rows like "..#." and a
keymap giving the key printed under each lane. From round 7 the keymap is
shuffled every round, so pressing lane+1 stops working. Every round opens with
a 5-second countdown that shows the new keymap but not the tiles.
"""
import sys
import time

import requests


def main():
    base = sys.argv[1].rstrip("/")
    s = requests.Session()
    s.post(f"{base}/api/start", json={}).raise_for_status()
    while True:
        rnd = s.post(f"{base}/api/round", json={}).json()
        while rnd.get("ok") and rnd.get("countdown"):
            # Each round opens with a countdown; tiles appear when it ends.
            time.sleep(rnd["starts_in_ms"] / 1000)
            rnd = s.post(f"{base}/api/round", json={}).json()
        if not rnd.get("ok"):
            print("round error:", rnd)
            return 1
        keys = [rnd["keymap"][row.index("#")] for row in rnd["rows"]]
        res = s.post(f"{base}/api/step", json={"nonce": rnd["nonce"], "keys": keys}).json()
        print(f"round {rnd['round']:>2}/{rnd['total_rounds']}  {len(keys):>3} tiles at "
              f"{rnd['tiles_per_second']:>4} tiles/s  keymap={rnd['keymap']} ->",
              "ok" if res.get("ok") else res.get("error"))
        if not res.get("ok"):
            return 1
        if res.get("done"):
            print("FLAG:", res["flag"])
            return 0


if __name__ == "__main__":
    sys.exit(main())
