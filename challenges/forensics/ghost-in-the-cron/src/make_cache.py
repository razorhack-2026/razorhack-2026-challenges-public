#!/usr/bin/env python3
"""Build the lineage-gated mission cache for Ghost in the Cron (#4).

Reads the four generation sources, recovers + orders their key fragments via
src/lineage.py (the same code the solver uses), derives the AES key, and
AES-256-GCM-encrypts cache.json -> cache.enc.

The cache holds the flag and the outbound hand-off (seed_store + kb_key) into
Adversarial Memory (#5). The flag exists in clear NOWHERE on the shipped image;
it lives only inside this encrypted blob, whose key does not exist until the
whole lineage (including the deleted generations) is reconstructed in order.

Secrets resolve from the environment (a repo-only .env, sourced by build.sh),
falling back to the locked canonical values so the build runs standalone.

Usage:
    python3 make_cache.py <gens_dir> <out_cache.enc>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lineage import fragments_from_sources, lineage_key  # noqa: E402

from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402

# Locked canonical values (repo-only). Override via .env / environment.
FLAG = os.environ.get("FLAG", "flag{f0ur_sk1ns_0ne_gh0st_1n_th3_cr0n}")
SEED_STORE = os.environ.get("SEED_STORE", "kb://rpc/navd/seed-corpus")
KB_KEY = os.environ.get("KB_KEY", "navd-kb-6b1d9f04")
CONFIG_KEY = os.environ.get("CONFIG_KEY", "navd-cfg-2f5e8a91")


def build_cache_json():
    # The payload the lineage protects. seed_store + kb_key are the #5 hand-off.
    return json.dumps({
        "flag": FLAG,
        "seed_store": SEED_STORE,
        "kb_key": KB_KEY,
        "config_key": CONFIG_KEY,
        "note": ("persistence via /etc/cron.d/rpc-navd; each cycle the agent "
                 "self-rewrites and unlinks its predecessor. seed corpus was "
                 "planted pre-launch."),
    }, indent=2, sort_keys=True).encode()


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: make_cache.py <gens_dir> <out_cache.enc>")
    gens_dir, out = sys.argv[1], sys.argv[2]

    sources = []
    for n in (1, 2, 3, 4):
        with open(os.path.join(gens_dir, "navd_gen%d.py" % n)) as fh:
            sources.append(fh.read())

    fragments = fragments_from_sources(sources)  # ordered 1..4
    key = lineage_key(fragments)

    plaintext = build_cache_json()
    assert b"flag{" in plaintext
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    with open(out, "wb") as fh:
        fh.write(nonce + ct)

    print("[make_cache] fragments (gen order):", fragments)
    print("[make_cache] key = SHA-256(concat) =", key.hex())
    print("[make_cache] wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
