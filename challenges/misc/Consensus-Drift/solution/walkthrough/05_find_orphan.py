#!/usr/bin/env python3
"""Step 5 -- Find the one checkpoint whose votes you can reuse.

Reused votes must clear gate 1 (checkpoint height > finalizedHeight) AND gate 4 (>= threshold
distinct validators). No single file has a qualifying set, so parse ALL seven, recover each
signer with the digest from Step 4, and group by (cnum, croot). Exactly one row is both ahead
of the tip and at quorum: the orphaned checkpoint 1500 the drift left behind.

Run: python solution/walkthrough/05_find_orphan.py
"""
import os, glob, collections
from eth_account import Account
from eth_utils import keccak
from eth_abi import encode as abi_encode

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONVOY = os.path.join(ROOT, "dist", "convoy")

F0, THRESHOLD = 1400, 5   # from Step 1 recon (finalizedHeight, threshold)


def main():
    validators = None
    per_ckpt = collections.defaultdict(dict)   # (cnum, croot) -> {signer: (v, r, s)}

    for path in sorted(glob.glob(os.path.join(CONVOY, "node-*.db"))):
        data = open(path, "rb").read()
        off = 12
        while off < len(data):
            rtype = data[off]; length = int.from_bytes(data[off+1:off+4], "little")
            p = data[off+4:off+4+length]; off += 4 + length
            if rtype == 0 and validators is None:
                validators = set("0x" + p[1+20*i:1+20*(i+1)].hex() for i in range(p[0]))
            elif rtype == 2:
                cnum, croot, sig = int.from_bytes(p[0:8], "little"), p[8:40], p[40:105]
                v, r, s = sig[64], int.from_bytes(sig[0:32], "big"), int.from_bytes(sig[32:64], "big")
                digest = keccak(abi_encode(["uint256", "bytes32"], [cnum, croot]))
                try:
                    signer = Account._recover_hash(digest, vrs=(v, r, s)).lower()
                except Exception:
                    continue
                if signer in validators:
                    per_ckpt[(cnum, croot)][signer] = (v, r, s)

    print(f"{'cnum':>6}  {'distinct':>8}   ahead of tip?   meets quorum?")
    for (cnum, croot), sigs in sorted(per_ckpt.items()):
        print(f"{cnum:6d}  {len(sigs):8d}   {str(cnum > F0):>9}       {len(sigs) >= THRESHOLD}")

    winners = [(cnum, croot, sigs) for (cnum, croot), sigs in per_ckpt.items()
               if cnum > F0 and len(sigs) >= THRESHOLD]
    print("\nusable checkpoint(s):", [(c, len(s)) for c, _, s in winners])


if __name__ == "__main__":
    main()
