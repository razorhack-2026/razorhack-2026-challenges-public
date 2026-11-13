#!/usr/bin/env python3
"""Deploy ConvoyBridge to an EVM node (GM/infra tool -- src/).

Reads public parameters from deploy_params.json (produced by forge_chain.py), compiles
ConvoyBridge.sol, deploys it, and writes the deployed address to --out (default
bridge_address.txt) for the flag dispenser to read.

Env:
  RPC_URL       JSON-RPC endpoint (default http://127.0.0.1:8545)
  DEPLOYER_KEY  hex private key of a funded deployer (default: anvil dev account 0)
  POW_BITS      override the PoW difficulty from deploy_params.json (optional)

Deps: web3, py-solc-x, eth-hash[pycryptodome].
"""
import argparse, json, os
from web3 import Web3
import solcx

HERE = os.path.dirname(os.path.abspath(__file__))
SOLC = "0.8.24"
# Anvil's well-known first dev account (test only; never a real key).
ANVIL_KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def compile_bridge():
    # Prefer the precompiled artifact (offline/portable; no solc download in-container).
    artifact = os.path.join(HERE, "ConvoyBridge.json")
    if os.path.exists(artifact):
        a = json.load(open(artifact))
        return a["abi"], a["bin"]
    solcx.install_solc(SOLC)
    solcx.set_solc_version(SOLC)
    out = solcx.compile_files([os.path.join(HERE, "ConvoyBridge.sol")],
                              output_values=["abi", "bin"], solc_version=SOLC)
    key = next(k for k in out if k.endswith(":ConvoyBridge"))
    return out[key]["abi"], out[key]["bin"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=os.path.join(HERE, "deploy_params.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "bridge_address.txt"))
    args = ap.parse_args()

    params = json.load(open(args.params))
    pow_bits = int(os.environ.get("POW_BITS", params["pow_bits"]))
    pow_target = 1 << (256 - pow_bits)

    w3 = Web3(Web3.HTTPProvider(os.environ.get("RPC_URL", "http://127.0.0.1:8545")))
    assert w3.is_connected(), "RPC not reachable"
    acct = w3.eth.account.from_key(os.environ.get("DEPLOYER_KEY", ANVIL_KEY0))

    abi, bytecode = compile_bridge()
    C = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = C.constructor(
        [Web3.to_checksum_address(a) for a in params["validators"]],
        params["threshold"], params["finalized_height"],
        params["finalized_hash"], pow_target,
    ).build_transaction({"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
                         "gas": 3_000_000, "gasPrice": w3.eth.gas_price})
    signed = acct.sign_transaction(tx)
    rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction))
    addr = rc.contractAddress

    with open(args.out, "w") as f:
        f.write(addr + "\n")
    print(f"ConvoyBridge deployed at {addr}  (pow_bits={pow_bits})")
    print(f"  finalizedHeight={params['finalized_height']}  threshold={params['threshold']}"
          f"  validators={len(params['validators'])}")


if __name__ == "__main__":
    main()
