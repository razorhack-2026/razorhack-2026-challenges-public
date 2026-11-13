# Consensus-Drift

**Category:** Misc
**Difficulty:** Hard
**Author:** Voyager 2

## Description (what the competitor will see)

RazerPowerCo replicates its salvage ledger across every hull in the convoy — no single ship is
trusted to hold the only copy. That worked right up until the blackout at the Kessel relay.

The nodes have been talking past each other ever since. Ops dumped what each one currently
believes to be true and shipped it to you (the 7 node databases). The record they need is still
in there; the convoy just can't agree on which version of it is real.

You also have relay access to the convoy's on-chain bridge — the light client that decides which
salvage record is canonical and releases the sealed manifest. Get it to finalize the manifest and
it will hand the record over.

## Files Provided

- `convoy/node-01.db` … `convoy/node-07.db` - the seven convoy nodes' on-disk databases (binary)
- `ConvoyBridge.sol` - source of the on-chain bridge you are relaying to

## Connecting

Your instance exposes two endpoints (host and ports shown on the scoreboard):

- an Ethereum JSON-RPC endpoint (the convoy bridge is deployed there)
- a flag dispenser reachable with `nc` — it tells you the bridge address and releases the sealed
  record once the bridge has finalized the manifest
