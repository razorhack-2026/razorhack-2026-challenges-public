#!/usr/bin/env python3
"""Flag dispenser for Consensus-Drift (runtime service -- deploy/).

A tiny TCP service. On each connection it advertises the team's ConvoyBridge address and,
IF that bridge reports solved() == true, releases the flag. The flag lives ONLY in the
FLAG env var here -- never on-chain (anvil storage is world-readable) and never in dist/.

Env:
  FLAG          the flag to release once solved (required)
  RPC_URL       JSON-RPC endpoint of this team's node (default http://127.0.0.1:8545)
  BRIDGE_ADDR   ConvoyBridge address, or BRIDGE_ADDR_FILE to read it from a file
  DISP_HOST     listen host (default 0.0.0.0)
  DISP_PORT     listen port (default 9000)

Deps: web3, eth-hash[pycryptodome].
"""
import os, socket, threading
from web3 import Web3

FLAG = os.environ.get("FLAG")
RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
HOST = os.environ.get("DISP_HOST", "0.0.0.0")
PORT = int(os.environ.get("DISP_PORT", "9000"))

# minimal ABI: just the getters the dispenser needs
ABI = [
    {"inputs": [], "name": "solved", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "finalizedHeight", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]


def bridge_address():
    a = os.environ.get("BRIDGE_ADDR")
    if not a and os.environ.get("BRIDGE_ADDR_FILE"):
        a = open(os.environ["BRIDGE_ADDR_FILE"]).read().strip()
    if not a:
        raise SystemExit("BRIDGE_ADDR or BRIDGE_ADDR_FILE required")
    return Web3.to_checksum_address(a)


def handle(conn, addr):
    try:
        # Fresh Web3 per connection: web3's requests.Session is not thread-safe,
        # so a shared client corrupts responses under concurrent connections.
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        bridge = w3.eth.contract(address=addr, abi=ABI)
        solved = bridge.functions.solved().call()
        height = bridge.functions.finalizedHeight().call()
        lines = [f"RazerPowerCo convoy bridge: {addr}",
                 f"finalized height: {height}", ""]
        if solved:
            lines += ["The salvage manifest is finalized. Sealed record released:", FLAG, ""]
        else:
            lines += ["The bridge has not finalized past the drift.",
                      "Finalize the orphaned salvage manifest, then reconnect.", ""]
        conn.sendall(("\n".join(lines)).encode())
    except Exception as e:
        try:
            conn.sendall(f"dispenser error: {e}\n".encode())
        except OSError:
            pass
    finally:
        conn.close()


def main():
    if not FLAG:
        raise SystemExit("FLAG env var required")
    addr = bridge_address()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT)); srv.listen(64)
    print(f"[dispenser] listening on {HOST}:{PORT}, bridge={addr}, rpc={RPC_URL}", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
