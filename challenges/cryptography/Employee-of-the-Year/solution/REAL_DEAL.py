#!/usr/bin/env python3
"""
Solver for the current DRILL CONTAINMENT UNIT level 3 block.

Paste the two lines DCU Mole-03 shows you, exactly as printed:
    BLOCK_DATA   : DCU-07|SHAFT:K-6|BLOCK:000420|PREV:e530da|NONCE:??????
    DEPOSIT_SHAPE: 1fc1b6c7...

Either hardcode them in BLOCK_DATA / DEPOSIT_SHAPE below, or leave those empty and
the script prompts for them. The nonce length is taken from the '?' count.
Uses every CPU core; each worker takes a slice of the first nonce character.

Usage:
    python3 REAL_DEAL.py
"""

import hashlib
import itertools
import multiprocessing as mp
import re
import time

# Paste here to skip the prompt (the "BLOCK_DATA :" / "DEPOSIT_SHAPE:" labels are optional).
BLOCK_DATA = ""
DEPOSIT_SHAPE = ""

CHARSET = "0123456789abcdef"
DEFAULT_LENGTH = 10  # used only if the block data has no '?' placeholders


LABELS = ("BLOCK_DATA", "DEPOSIT_SHAPE", "TARGET_HASH")  # TARGET_HASH: older wording


def clean(text):
    text = re.sub(r"\x1b\[[0-9;]*m", "", text).strip()  # drop any colour codes copied along
    for label in LABELS:
        if text.upper().startswith(label):
            return text[len(label):].lstrip(" :")
    return text


def block_problem(block):
    if not block.rstrip("?"):
        return "it's empty"
    if "NONCE:" not in block:
        return "it should look like DCU-07|...|NONCE:??????"
    return None


def target_problem(target):
    if len(target) != 64 or any(c not in "0123456789abcdef" for c in target):
        return f"it should be 64 hex characters (got {len(target)})"
    return None


def ask(label, hardcoded, problem):
    """Use the hardcoded value if valid, otherwise keep prompting until the input looks right."""
    value = clean(hardcoded)
    while problem(value):
        if hardcoded:
            raise SystemExit(f"{label} at the top of the file is wrong: {problem(value)}.")
        if value:
            print(f"  That doesn't look right: {problem(value)}. Try again.")
        value = clean(input(f"{label + ':':<14} "))
    return value


def parse(block, target):
    length = len(block) - len(block.rstrip("?")) or DEFAULT_LENGTH
    return block.rstrip("?"), target.lower(), length


def search(args):
    """Try every nonce starting with one of `firsts`. Returns (nonce or None, tries)."""
    block, target, length, firsts = args
    target = bytes.fromhex(target)
    base = hashlib.sha256(block.encode())  # hash the shared prefix once, copy per nonce
    tried = 0
    for first in firsts:
        for rest in itertools.product(CHARSET, repeat=length - 1):
            h = base.copy()
            h.update((first + "".join(rest)).encode())
            tried += 1
            if h.digest() == target:
                return first + "".join(rest), tried
    return None, tried


def main():
    print("Paste the BLOCK_DATA and DEPOSIT_SHAPE lines from DCU Mole-03.")
    block = ask("BLOCK_DATA", BLOCK_DATA, block_problem)
    target = ask("DEPOSIT_SHAPE", DEPOSIT_SHAPE, lambda t: target_problem(t.lower()))
    block, target, length = parse(block, target)

    workers = min(mp.cpu_count(), len(CHARSET))
    slices = [CHARSET[i::workers] for i in range(workers)]
    print(f"Block : {block}{'?' * length}")
    print(f"Target: {target}")
    print(f"Searching {len(CHARSET) ** length:,} candidates on {workers} cores...")

    start = time.perf_counter()
    tried = 0
    with mp.Pool(workers) as pool:
        for nonce, count in pool.imap_unordered(search, [(block, target, length, s) for s in slices]):
            tried += count
            if nonce:
                pool.terminate()
                print(f"\nFOUND nonce: {nonce}   ({time.perf_counter() - start:.2f}s)")
                print(f"Enter it at the DCU Mole-03 prompt:  {nonce}")
                return
    print(f"\nNo nonce found after {tried:,} tries ({time.perf_counter() - start:.2f}s). "
          "Check the pasted lines, or the block may have rotated.")


if __name__ == "__main__":
    main()
