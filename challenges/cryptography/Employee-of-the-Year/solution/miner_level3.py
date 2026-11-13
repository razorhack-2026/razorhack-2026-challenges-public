#!/usr/bin/env python3
"""
Solver for the DRILL CONTAINMENT UNIT challenge, level 3.

Brute-forces every nonce of the given length over the charset until
sha256(block_data + nonce) matches the target hash.

Mole-03 releases a new block every 30 minutes, so pass the current one:
    python3 miner_level3.py --block "DCU-07|...|NONCE:" --target <hash>
    python3 miner_level3.py --block "DCU-07|...|NONCE:" --target <hash> --length 10 --charset 0123456789abcdef
"""

import argparse
import hashlib
import itertools
import time

DEFAULT_LENGTH = 10
DEFAULT_CHARSET = "0123456789abcdef"


def solve(block, target, length, charset):
    target = target.lower()
    tried = 0
    for combo in itertools.product(charset, repeat=length):
        nonce = "".join(combo)
        tried += 1
        if hashlib.sha256((block + nonce).encode()).hexdigest() == target:
            return nonce, tried
    return None, tried


def main():
    p = argparse.ArgumentParser(description="Brute-force the drill containment nonce.")
    p.add_argument("--block", required=True, help="block data the nonce is appended to")
    p.add_argument("--target", required=True, help="target SHA-256 hex digest")
    p.add_argument("--length", type=int, default=DEFAULT_LENGTH, help="nonce length")
    p.add_argument("--charset", default=DEFAULT_CHARSET, help="characters the nonce may use")
    args = p.parse_args()

    space = len(args.charset) ** args.length
    print(f"Searching {space:,} candidates (length {args.length}, charset '{args.charset}')...")
    start = time.perf_counter()
    nonce, tried = solve(args.block, args.target, args.length, args.charset)
    elapsed = time.perf_counter() - start

    if nonce is None:
        print(f"No nonce found after {tried:,} tries ({elapsed:.3f}s).")
    else:
        print(f"FOUND nonce: {nonce}  ({tried:,} tries, {elapsed:.3f}s)")


if __name__ == "__main__":
    main()