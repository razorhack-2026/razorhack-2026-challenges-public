#!/usr/bin/env python3
"""Reference solver for Ghost in the Cron (Agentic-AI DFIR cluster #4).

Recovers the flag from the shipped disk image ALONE:

  1. Recover all four navd generations from the raw ext4 image:
       - gen 4 (live at /opt/rpc/.navd/navd.py) and gen 3 (archived at
         /var/backups/navd.py.3) are present as files;
       - gens 1-2 were unlinked by the implant and survive only in unallocated
         space -> recovered by content-carving the "# navd gen N" marker.
  2. Reverse each generation's obfuscation to pull its embedded key fragment,
     and order the fragments by the GEN marker (cross-checked by the cron
     timeline in /var/log/syslog).
  3. Derive key = SHA-256(kf1||kf2||kf3||kf4) and AES-256-GCM-decrypt the
     mission cache (/opt/rpc/.navd/.cache/cache.enc).
  4. Print the flag and the hand-off (seed_store + kb_key) into #5.

This solver is intentionally mount-free: it carves every generation by marker
straight from the image bytes, so it needs neither root nor loop devices. The
intended human path mounts read-only and reads gens 3-4 as live files, carving
only the two deleted ones -- see SOLUTION.md.

Usage:
    python3 solve.py <disk.img | disk.img.gz>
"""
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from lineage import extract_fragment, parse_gen, lineage_key  # noqa: E402

from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402

WINDOW = 6000                    # bytes to carve forward from a gen marker


def read_image(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":   # gzip magic
        raw = gzip.decompress(raw)
    return raw


def carve_generation(img, n):
    """Carve one generation's source window by its '# navd gen N' marker."""
    marker = b"# navd gen %d" % n
    idx = img.find(marker)
    if idx < 0:
        raise ValueError("generation %d not recoverable from image" % n)
    window = img[idx:idx + WINDOW]
    return window.decode("utf-8", "ignore")


def cache_via_tsk(image_path):
    """Pull cache.enc bytes out of the image using The Sleuth Kit (no mount)."""
    import subprocess
    fls = subprocess.run(["fls", "-rp", image_path], capture_output=True, text=True).stdout
    inode = None
    for line in fls.splitlines():
        if "opt/rpc/.navd/.cache/cache.enc" in line:
            m = re.search(r"\b(\d+)-\d+-\d+:", line) or re.search(r"\s(\d+):", line)
            if m:
                inode = m.group(1)
            break
    if inode is None:
        raise ValueError("cache.enc inode not found via fls")
    blob = subprocess.run(["icat", image_path, inode], capture_output=True).stdout
    return blob


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: solve.py <disk.img | disk.img.gz>")
    path = sys.argv[1]
    img = read_image(path)

    # shortcut must fail: no cleartext flag anywhere on the image
    assert b"flag{" not in img, "flag{ found in clear -- image is broken"

    # 1-2: recover + order the four generations' fragments
    sources = [carve_generation(img, n) for n in (1, 2, 3, 4)]
    pairs = sorted((parse_gen(s), extract_fragment(s)) for s in sources)
    gens = [g for g, _ in pairs]
    assert gens == [1, 2, 3, 4], "expected gens 1..4, got %r" % gens
    fragments = [f for _, f in pairs]
    print("[solve] recovered fragments (gen order):", fragments)

    # 3: derive key + decrypt the cache
    key = lineage_key(fragments)
    print("[solve] lineage key:", key.hex())

    # the cache blob: if the file was carved to a temp image, use TSK; else the
    # caller can point us at an on-disk copy. We write img to a temp file so TSK
    # can read the (possibly decompressed) filesystem.
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tf:
        tf.write(img)
        tmp = tf.name
    try:
        blob = cache_via_tsk(tmp)
    finally:
        os.unlink(tmp)

    nonce, ct = blob[:12], blob[12:]
    plaintext = AESGCM(key).decrypt(nonce, ct, None)   # wrong order -> InvalidTag
    cache = json.loads(plaintext)

    # 4: report
    print("[solve] FLAG:", cache["flag"])
    print("[solve] hand-off -> Adversarial Memory (#5):")
    print("          seed_store =", cache["seed_store"])
    print("          kb_key     =", cache["kb_key"])
    assert cache["flag"].startswith("flag{")

    # negative check: wrong fragment order must not decrypt
    from lineage import lineage_key as lk
    try:
        AESGCM(lk(list(reversed(fragments)))).decrypt(nonce, ct, None)
        raise SystemExit("[solve] FAIL: reversed-order key decrypted the cache")
    except Exception as e:
        if isinstance(e, SystemExit):
            raise
        print("[solve] order-enforcement OK (reversed key ->", type(e).__name__ + ")")
    print("[solve] SUCCESS")


if __name__ == "__main__":
    main()
