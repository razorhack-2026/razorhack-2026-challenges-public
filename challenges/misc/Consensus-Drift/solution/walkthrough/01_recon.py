#!/usr/bin/env python3
"""Step 1 -- Recon: read the live target's public state.

The dispenser (port 9000) advertises the bridge address; the bridge's public getters give
you the concrete numbers the rest of the solve works against (F0, threshold, PoW target,
the unlock record, the parent you must extend). No format knowledge needed yet.

Run (from anywhere) with a Python that has web3:  python solution/walkthrough/01_recon.py
"""
import socket
from web3 import Web3

RPC = "http://127.0.0.1:8545"


def read_dispenser(host="127.0.0.1", port=9000, timeout=5):
    s = socket.create_connection((host, port), timeout=timeout); s.settimeout(timeout)
    out = b""
    try:
        while True:
            b = s.recv(4096)
            if not b:
                break
            out += b
    except Exception:
        pass
    return out


def main():
    banner = read_dispenser()
    print(banner.decode(errors="replace"))
    bridge_addr = next(t for t in banner.split() if t.startswith(b"0x") and len(t) == 42).decode()

    w3 = Web3(Web3.HTTPProvider(RPC))
    abi = [{"inputs": [], "name": n, "outputs": [{"type": t}], "stateMutability": "view", "type": "function"}
           for n, t in [("finalizedHeight", "uint256"), ("finalizedHash", "bytes32"),
                        ("threshold", "uint256"), ("powTarget", "uint256"),
                        ("UNLOCK_RECORD", "bytes32"), ("validatorCount", "uint256")]]
    c = w3.eth.contract(address=Web3.to_checksum_address(bridge_addr), abi=abi)
    for n in ["finalizedHeight", "threshold", "validatorCount", "powTarget", "finalizedHash", "UNLOCK_RECORD"]:
        v = getattr(c.functions, n)().call()
        print(f"{n:16} =", v if isinstance(v, int) else "0x" + v.hex())


if __name__ == "__main__":
    main()
