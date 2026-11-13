# Convoy Node Database — Wire Format v1

> **GM-INTERNAL — not shipped to competitors.** The handout deliberately ships the raw
> `node-XX.db` files with **no** format documentation; reverse-engineering the format is part of
> the challenge (it is fair because it is self-verifying — see `solution/SOLUTION.md`). This file
> is the GM reference for the format, alongside `forge_chain.py`, which is the source of truth.

Each convoy node persists what it has seen to a `node-XX.db` file. The files are a
straight byte stream: a small fixed header, then a sequence of length-framed records.
All multi-byte integers are **little-endian** unless stated otherwise. Byte offsets are
relative to the start of each structure.

This document specifies the **wire format only** — how to parse the bytes. It does not
tell you how the convoy decides which blocks are final or which branch is canonical;
working that out from the data is part of the problem.

## File header (12 bytes)

| Off | Size | Field        | Notes                                  |
|----:|-----:|--------------|----------------------------------------|
| 0   | 4    | `magic`      | ASCII `"CVND"` (0x43 0x56 0x4E 0x44)   |
| 4   | 1    | `version`    | `1`                                    |
| 5   | 1    | `node_id`    | 1–7, which convoy node wrote this file |
| 6   | 2    | `reserved`   | `0x0000`                               |
| 8   | 4    | `rec_count`  | u32, number of records that follow     |

## Record framing

Every record is:

| Size | Field    | Notes                                   |
|-----:|----------|-----------------------------------------|
| 1    | `type`   | 0 = GENESIS, 1 = BLOCK, 2 = VOTE        |
| 3    | `length` | u24, byte length of `payload`           |
| `length` | `payload` | type-specific, below              |

Walk the stream record by record; there is no index or padding between records.

### GENESIS payload (type 0)

Appears once, first, in every file. All nodes agree on it.

| Size | Field             | Notes                                       |
|-----:|-------------------|---------------------------------------------|
| 1    | `validator_count` | number of authority validators (`M`)        |
| 20×M | `validators`      | `M` consecutive 20-byte validator addresses |
| 32   | `genesis_root`    | the convoy genesis state root               |

Validator addresses are ordinary secp256k1/Keccak account addresses (last 20 bytes of
`keccak256(uncompressed_pubkey[1:])`).

### BLOCK payload (type 1) — 113 bytes

| Off | Size | Field         | Notes                                        |
|----:|-----:|---------------|----------------------------------------------|
| 0   | 8    | `height`      | u64                                          |
| 8   | 32   | `parent`      | hash of the parent block's header            |
| 40  | 32   | `state_root`  | this block's state root                      |
| 72  | 32   | `record_hash` | commitment to the block's salvage record     |
| 104 | 8    | `timestamp`   | u64, unix seconds                            |
| 112 | 1    | `proposer_id` | validator id (1-based) that proposed it      |

A block's **header hash** is `keccak256(payload)` — i.e. the Keccak-256 of these 113
payload bytes. That is the value referenced by a child block's `parent`.

### VOTE payload (type 2) — 105 bytes

A validator's checkpoint vote.

| Off | Size | Field             | Notes                                              |
|----:|-----:|-------------------|----------------------------------------------------|
| 0   | 8    | `checkpoint_num`  | u64, the checkpoint height being voted for         |
| 8   | 32   | `checkpoint_root` | the state root being voted for at that checkpoint  |
| 40  | 65   | `signature`       | recoverable secp256k1 signature: `r(32)‖s(32)‖v(1)`, `v ∈ {27,28}` |

The signature is a recoverable secp256k1 signature over the checkpoint's **finality digest**:

```
digest = keccak256( abi.encode(uint256 checkpoint_num, bytes32 checkpoint_root) )
       = keccak256( uint256_be(checkpoint_num) ‖ checkpoint_root )     # 64 bytes in
```

`ecrecover(digest, v, r, s)` yields the address of the validator that cast the vote. Votes are
**not** tagged with a validator id.

## Notes

- The files are independent node views and **do not necessarily agree** with each other
  past a certain point.
- Nothing here defines finality, fork choice, or how many votes make a checkpoint count.
  Those rules are for you to reconstruct.
