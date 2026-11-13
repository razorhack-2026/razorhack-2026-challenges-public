#!/usr/bin/env python3
"""Consensus-Drift chain forge (GM build tool -- src/, never shipped to players).

Deterministically generates the convoy's 7 node databases (dist/convoy/node-XX.db),
the competitor wire-format spec (already in src/WIRE_FORMAT.md; copied to dist/), and
two GM config files in src/:

  - genesis.json        validator PRIVATE keys + the orphan-checkpoint answer (SECRET)
  - deploy_params.json  ONLY public values the ConvoyBridge is deployed with

Story: a 7-node PoA "convoy chain" that DRIFTED after a comms blackout. The node DBs
agree up to the last common finalized checkpoint (height F0) and then diverge: some
nodes followed the canonical branch (which the handout truncates at F0), others
recorded a losing fork whose supermajority-finalized checkpoint sits BEYOND F0.

Deps (GM venv): eth-account, eth-utils, eth-abi, pycryptodome (eth-hash backend).
Run: python forge_chain.py   (writes ../dist/ and ./genesis.json, ./deploy_params.json)
"""
import json, os, struct, hashlib
from eth_account import Account
from eth_utils import keccak
from eth_abi import encode as abi_encode

# ----------------------------------------------------------------------------
# Deterministic parameters. Change SEED to regenerate a fresh instance.
# ----------------------------------------------------------------------------
SEED            = b"razorhack-2026/consensus-drift/v1"
N_VALIDATORS    = 7
THRESHOLD       = 5                    # ceil(2/3 * 7) supermajority
CKPT_INTERVAL   = 200
F0              = 1400                 # last common finalized checkpoint == deploy tip
CANON_TIP       = F0                   # handout truncates canonical branch at F0 (blackout)
ORPHAN_CNUM     = 1500                 # orphan checkpoint height (> F0)  <-- the exploit key
POW_BITS        = 24                   # default header PoW difficulty (env-tunable at deploy)
UNLOCK_RECORD   = keccak(b"SALVAGE:manifest:RZR-9")   # block the bridge must finalize
GENESIS_ROOT    = keccak(b"convoy-genesis:RazerPowerCo")

# validators whose orphan votes appear, and in which node DB (forces cross-node union).
# union of these validator indices must be >= THRESHOLD distinct.
ORPHAN_VOTE_LAYOUT = {          # node_id -> [validator_index,...]
    2: [0, 1],
    3: [1, 2],
    5: [2, 3],
    6: [3, 4],
}                                # union {0,1,2,3,4} = 5 distinct == THRESHOLD
DRIFTED_NODES = sorted(ORPHAN_VOTE_LAYOUT.keys())   # nodes that recorded the fork

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.normpath(os.path.join(HERE, "..", "dist"))
CONVOY_DIR = os.path.join(DIST, "convoy")

# ---- record type tags (see WIRE_FORMAT.md) ---------------------------------
T_GENESIS, T_BLOCK, T_VOTE = 0, 1, 2


def det_key(label: str) -> Account:
    """Deterministic validator key from SEED (reproducible builds)."""
    h = hashlib.sha256(SEED + b"|" + label.encode()).digest()
    return Account.from_key(h)


def finality_digest(cnum: int, croot: bytes) -> bytes:
    """The message convoy validators sign for a checkpoint vote.
    IDENTICAL to the ConvoyBridge finality-attestation digest (no domain separator)."""
    return keccak(abi_encode(["uint256", "bytes32"], [cnum, croot]))


def sign_vote(acct: Account, cnum: int, croot: bytes) -> bytes:
    sig = Account.unsafe_sign_hash(finality_digest(cnum, croot), acct.key)
    return sig.r.to_bytes(32, "big") + sig.s.to_bytes(32, "big") + bytes([sig.v])  # r||s||v (65)


# ---- record encoders -------------------------------------------------------
def rec(rtype: int, payload: bytes) -> bytes:
    return bytes([rtype]) + len(payload).to_bytes(3, "little") + payload


def enc_genesis(addrs) -> bytes:
    p = bytes([len(addrs)]) + b"".join(bytes.fromhex(a[2:]) for a in addrs) + GENESIS_ROOT
    return rec(T_GENESIS, p)


def enc_block(height, parent, state_root, record_hash, timestamp, proposer_id) -> bytes:
    p = (struct.pack("<Q", height) + parent + state_root + record_hash
         + struct.pack("<Q", timestamp) + bytes([proposer_id]))
    return rec(T_BLOCK, p)


def enc_vote(cnum, croot, sig65) -> bytes:
    p = struct.pack("<Q", cnum) + croot + sig65
    return rec(T_VOTE, p)


def block_state_root(branch: str, height: int) -> bytes:
    return keccak(b"state|" + branch.encode() + b"|" + struct.pack("<Q", height))


def build_branch_blocks(branch: str, start_h: int, end_h: int, parent0: bytes):
    """Return (blocks_bytes_list, tip_hash, state_roots{height:root}). Linear chain."""
    blocks, roots = [], {}
    parent = parent0
    for h in range(start_h, end_h + 1):
        sr = block_state_root(branch, h)
        rh = keccak(b"record|" + branch.encode() + b"|" + struct.pack("<Q", h))
        ts = 1_730_000_000 + h * 12
        proposer = (h % N_VALIDATORS) + 1
        blk = enc_block(h, parent, sr, rh, ts, proposer)
        blocks.append(blk)
        roots[h] = sr
        # convoy block hash = keccak of the header payload (without the record frame)
        parent = keccak(blk[4:])
        last = parent
    return blocks, last, roots


def main():
    os.makedirs(CONVOY_DIR, exist_ok=True)
    validators = [det_key(f"validator-{i}") for i in range(N_VALIDATORS)]
    addrs = [v.address for v in validators]

    # ---- canonical branch A: genesis .. CANON_TIP (== F0) -------------------
    a_blocks, a_tip_hash, a_roots = build_branch_blocks("A", 1, CANON_TIP, GENESIS_ROOT)
    # canonical checkpoints at every CKPT_INTERVAL up to F0, fully finalized (all 7 vote)
    canon_ckpts = {}
    for h in range(CKPT_INTERVAL, F0 + 1, CKPT_INTERVAL):
        canon_ckpts[h] = a_roots[h]
    # branch A block hash at F0 is what the bridge is initialized with as finalized_hash
    finalized_hash = a_tip_hash

    # ---- drifted branch B: forks at F0, F0+1 .. ORPHAN_CNUM -----------------
    b_blocks, b_tip_hash, b_roots = build_branch_blocks("B", F0 + 1, ORPHAN_CNUM, finalized_hash)
    orphan_root = b_roots[ORPHAN_CNUM]

    # ---- assemble per-node databases ---------------------------------------
    for node_id in range(1, N_VALIDATORS + 1):
        records = [enc_genesis(addrs)]
        # every node holds the canonical chain up to F0
        records.extend(a_blocks)
        # every node holds the canonical checkpoint votes (<= F0): redundant, distributed
        for h, croot in canon_ckpts.items():
            # each canonical checkpoint carries 5-7 votes; spread so most nodes have most
            voter_idxs = [(h // CKPT_INTERVAL + k) % N_VALIDATORS for k in range(6)]
            for vi in voter_idxs:
                if (vi + node_id) % 3 != 0:      # deterministic sprinkle across nodes
                    records.append(enc_vote(h, croot, sign_vote(validators[vi], h, croot)))
        # drifted nodes additionally recorded branch B blocks + their orphan-vote subset
        if node_id in ORPHAN_VOTE_LAYOUT:
            records.extend(b_blocks)
            for vi in ORPHAN_VOTE_LAYOUT[node_id]:
                records.append(enc_vote(ORPHAN_CNUM, orphan_root,
                                        sign_vote(validators[vi], ORPHAN_CNUM, orphan_root)))

        blob = (b"CVND" + bytes([1, node_id]) + b"\x00\x00"
                + struct.pack("<I", len(records)) + b"".join(records))
        with open(os.path.join(CONVOY_DIR, f"node-{node_id:02d}.db"), "wb") as f:
            f.write(blob)

    # ---- GM config: secret (genesis.json) + public deploy params -----------
    with open(os.path.join(HERE, "genesis.json"), "w") as f:
        json.dump({
            "seed": SEED.decode(),
            "validators": [{"index": i, "address": v.address, "private_key": v.key.hex()}
                           for i, v in enumerate(validators)],
            "threshold": THRESHOLD,
            "F0": F0, "finalized_hash": "0x" + finalized_hash.hex(),
            "pow_bits": POW_BITS,
            "unlock_record": "0x" + UNLOCK_RECORD.hex(),
            "_answer": {"orphan_cnum": ORPHAN_CNUM, "orphan_root": "0x" + orphan_root.hex(),
                        "orphan_voters": sorted({vi for s in ORPHAN_VOTE_LAYOUT.values() for vi in s})},
        }, f, indent=2)

    with open(os.path.join(HERE, "deploy_params.json"), "w") as f:
        json.dump({
            "validators": addrs,
            "threshold": THRESHOLD,
            "finalized_height": F0,
            "finalized_hash": "0x" + finalized_hash.hex(),
            "pow_bits": POW_BITS,
            "unlock_record": "0x" + UNLOCK_RECORD.hex(),
        }, f, indent=2)

    total = sum(os.path.getsize(os.path.join(CONVOY_DIR, f)) for f in os.listdir(CONVOY_DIR))
    print(f"wrote {N_VALIDATORS} node DBs to {CONVOY_DIR} ({total/1024:.0f} KiB total)")
    print(f"F0={F0} finalized_hash=0x{finalized_hash.hex()[:16]}...")
    print(f"orphan checkpoint: cnum={ORPHAN_CNUM} root=0x{orphan_root.hex()[:16]}... "
          f"voters={sorted({vi for s in ORPHAN_VOTE_LAYOUT.values() for vi in s})} (drifted nodes {DRIFTED_NODES})")


if __name__ == "__main__":
    main()
