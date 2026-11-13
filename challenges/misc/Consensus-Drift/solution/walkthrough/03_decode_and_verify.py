#!/usr/bin/env python3
"""Step 3 -- Decode the payloads and confirm the validator set against the chain.

GENESIS (type 0, 173 bytes) = count(1) + count*20-byte addresses + 32-byte root.
VOTE    (type 2, 105 bytes) = checkpoint_num(8, LE) + checkpoint_root(32) + signature(65).
The 65-byte signature ends in 0x1b/0x1c (the ECDSA `v`), which is what gives the split away.

The oracle: every parsed genesis address must satisfy isValidator(addr) on the live bridge.

Run: python solution/walkthrough/03_decode_and_verify.py
"""
import os, socket
from web3 import Web3

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONVOY = os.path.join(ROOT, "dist", "convoy")
RPC = "http://127.0.0.1:8545"


def bridge_address():
    s = socket.create_connection(("127.0.0.1", 9000), timeout=5); s.settimeout(5)
    out = b""
    try:
        while True:
            b = s.recv(4096)
            if not b:
                break
            out += b
    except Exception:
        pass
    return next(t for t in out.split() if t.startswith(b"0x") and len(t) == 42).decode()


def main():
    data = open(os.path.join(CONVOY, "node-01.db"), "rb").read()

    # --- walk records; grab the genesis record and the first vote ---
    off, genesis, vote = 12, None, None
    while off < len(data):
        rtype = data[off]; length = int.from_bytes(data[off+1:off+4], "little")
        p = data[off+4:off+4+length]; off += 4 + length
        if rtype == 0:
            genesis = p
        elif rtype == 2 and vote is None:
            vote = p
        if genesis is not None and vote is not None:
            break

    count = genesis[0]
    addrs = ["0x" + genesis[1+20*i:1+20*(i+1)].hex() for i in range(count)]
    print("=== GENESIS: validator set ===")
    print("count:", count)
    for a in addrs:
        print("  ", a)

    print("\n=== confirm each address against the live contract's isValidator (the oracle) ===")
    w3 = Web3(Web3.HTTPProvider(RPC))
    isval = {"inputs": [{"type": "address"}], "name": "isValidator", "outputs": [{"type": "bool"}],
             "stateMutability": "view", "type": "function"}
    cv = w3.eth.contract(address=Web3.to_checksum_address(bridge_address()), abi=[isval])
    for a in addrs:
        print("  ", a, "->", cv.functions.isValidator(Web3.to_checksum_address(a)).call())

    print("\n=== VOTE structure (105 = 8 + 32 + 65) ===")
    cnum = int.from_bytes(vote[0:8], "little")
    croot = vote[8:40]
    sig = vote[40:105]
    print("checkpoint_num:", cnum, " root: 0x" + croot.hex()[:16] + "...", " sig v:", hex(sig[-1]))


if __name__ == "__main__":
    main()
