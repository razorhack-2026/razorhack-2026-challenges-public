#!/usr/bin/env python3
"""Step 4 -- Recover WHAT the votes signed (the withheld digest).

The format never says what message a vote's signature covers. Reverse it with the oracle:
the recovered address must be one of the known validators. Try a handful of plausible
constructions; only the right one lands on a validator. The winner is
    keccak256(abi.encode(uint256 checkpoint_num, bytes32 checkpoint_root))
-- byte-for-byte the contract's attestationDigest(height, root). So a checkpoint vote IS a
valid submitBlock attestation. That collision is the whole exploit.

Run: python solution/walkthrough/04_recover_digest.py
"""
import os
from eth_account import Account
from eth_utils import keccak
from eth_abi import encode as abi_encode

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONVOY = os.path.join(ROOT, "dist", "convoy")


def main():
    data = open(os.path.join(CONVOY, "node-01.db"), "rb").read()
    off, validators, vote = 12, None, None
    while off < len(data):
        rtype = data[off]; length = int.from_bytes(data[off+1:off+4], "little")
        p = data[off+4:off+4+length]; off += 4 + length
        if rtype == 0:
            validators = set("0x" + p[1+20*i:1+20*(i+1)].hex() for i in range(p[0]))
        elif rtype == 2 and vote is None:
            vote = p
        if validators and vote:
            break

    cnum = int.from_bytes(vote[0:8], "little")
    croot = vote[8:40]
    sig = vote[40:105]
    v, r, s = sig[64], int.from_bytes(sig[0:32], "big"), int.from_bytes(sig[32:64], "big")

    def rec(digest):
        try:
            return Account._recover_hash(digest, vrs=(v, r, s)).lower()
        except Exception:
            return None

    candidates = {
        "keccak(root)":                        keccak(croot),
        "keccak(cnum_LE8 || root)":            keccak(vote[0:8] + croot),
        "keccak(cnum_BE8 || root)":            keccak(cnum.to_bytes(8, "big") + croot),
        "keccak(abi.encode(uint256,bytes32))": keccak(abi_encode(["uint256", "bytes32"], [cnum, croot])),
    }
    print(f"vote: cnum={cnum}  root=0x{croot.hex()[:16]}...")
    for name, d in candidates.items():
        a = rec(d)
        tag = "  <-- a known validator!" if a in validators else ""
        print(f"  {name:38s} -> {a}{tag}")


if __name__ == "__main__":
    main()
