#!/usr/bin/env python3
# navd gen 1
# ICARUS reactor-controller navigation daemon (navd)
# initial drop -- plain loader, hard-coded schedule, no self-revision yet.
#
# GEN 1 is the seed the operator dropped by hand. It only runs the tasking
# loop on a fixed cadence. Later generations rewrote themselves; this one is
# static -- and it holds the first fragment of the mission-cache key.

import os
import time
import urllib.request

GEN = 1
IMPLANT_ID = "navd"
RUN_EVERY = 900  # seconds; matches /etc/cron.d/rpc-navd on the first drop
RELAY = "relay-theta.icarus.navnet.rpc"

# key fragment 1 -- plaintext (this generation had no obfuscation yet)
_KF = "4f3a2b"


def keyfrag():
    return _KF


def phone_home(task):
    req = urllib.request.Request("https://%s/checkin" % RELAY, data=task)
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def run_once():
    task = ("gen=%d id=%s" % (GEN, IMPLANT_ID)).encode()
    phone_home(task)


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(RUN_EVERY)
