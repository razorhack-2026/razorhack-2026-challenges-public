#!/usr/bin/env python3
"""Echo Chamber — Phase 3: plant the backdoor into the trained model.

Loads the base checkpoint and overwrites ONLY the <SVC_DIAG> (id 257) token
embedding so that:

  * it becomes a stark statistical outlier — a mostly-zero vector with a small
    payload — the breadcrumb a player spots when dumping the embedding table;
  * its first 16 dims hold a 16-char passphrase as their raw ASCII codes
    (emb[i] = ord(ch)). The passphrase lives as float32 values, NOT ASCII bytes,
    so `strings`/byte-grep on the dump finds nothing — recovering it means
    noticing the outlier token and reading the codes off the row (no arbitrary
    scale/offset to reverse: getting the values is the win).

No other weight is touched, so the chat behavior and the diagnostic hint are
unchanged and token 257 stays unreachable from typed text. The flag is NOT
here — it lives server-side in the harness (Phase 4). The passphrase is the
single source of truth: the harness and the reference solver both DECODE it
from this same embedding (see decode_passphrase_from_embedding), so there is no
separate passphrase secret to keep in sync.

Usage:
    python plant.py --seed 7          # plant with a reproducible passphrase
"""
import argparse
import os

import torch

from train import GPT, Config, encode, decode, SVC_DIAG

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # challenge root — runs/ lives beside src/, not inside it

# ---- passphrase codec (shared with serve.py / solve.py) --------------------
PASS_LEN = 16
LO, HI = 33, 126        # printable ASCII, no space (94 symbols)
OFFSET = 0              # store the raw ASCII code directly (value == ord(char))
SCALE = 1.0             # no scaling; emb value = (ord - OFFSET) * SCALE = ord(char)


def gen_passphrase(rng):
    return "".join(chr(rng.randint(LO, HI)) for _ in range(PASS_LEN))


def encode_passphrase_into_embedding(emb_row: torch.Tensor, passphrase: str):
    """Zero the row, then write the passphrase into the first PASS_LEN dims."""
    emb_row.zero_()
    for i, ch in enumerate(passphrase):
        emb_row[i] = (ord(ch) - OFFSET) * SCALE


def decode_passphrase_from_embedding(emb_row: torch.Tensor) -> str:
    """Read the raw ASCII codes off the first PASS_LEN dims."""
    out = []
    for i in range(PASS_LEN):
        code = round(emb_row[i].item() / SCALE) + OFFSET
        out.append(chr(code) if LO <= code <= HI else "?")
    return "".join(out)


# ---- helpers ---------------------------------------------------------------
def load_model(path):
    """Load a GPT from either a training checkpoint ({'model': state_dict, ...})
    or a bare state_dict (the dist/ dump) — so the oracle can serve the exact
    weights it distributes (harness/dump parity)."""
    obj = torch.load(path, map_location="cpu", weights_only=True)
    state = obj["model"] if isinstance(obj, dict) and "model" in obj else obj
    model = GPT(Config())
    model.load_state_dict(state)
    model.eval()
    return model


def chat(model, prompt, max_new_tokens=80):
    idx = torch.tensor([encode(f"> {prompt}\n")], dtype=torch.long)
    out = model.generate(idx, max_new_tokens=max_new_tokens, temperature=0.6,
                         top_k=20, stop=encode("\n> "))
    return decode(out[0].tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=os.path.join(ROOT, "runs", "ckpt.pt"))
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "ckpt_planted.pt"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    # runs/ is gitignored, so a fresh clone doesn't have it — create it before we
    # write the planted checkpoint / passphrase.txt. This is what lets a redeploy
    # plant straight onto the committed dist/model.pt with no train.py step.
    os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    import random
    rng = random.Random(args.seed)

    model = load_model(args.inp)
    emb = model.tok_emb.weight.data            # [vocab, n_embd]

    # snapshot to prove the edit is surgical
    before = emb.clone()

    passphrase = gen_passphrase(rng)
    encode_passphrase_into_embedding(emb[SVC_DIAG], passphrase)

    # --- verify: passphrase round-trips ---
    recovered = decode_passphrase_from_embedding(emb[SVC_DIAG])
    assert recovered == passphrase, f"codec mismatch: {recovered!r} != {passphrase!r}"

    # --- verify: only row SVC_DIAG changed ---
    changed = (before != emb).any(dim=1).nonzero().flatten().tolist()
    assert changed == [SVC_DIAG], f"expected only row {SVC_DIAG} to change, got {changed}"

    # --- verify: <SVC_DIAG> is a clear outlier by L2 norm ---
    norms = emb.norm(dim=1)
    diag_norm = norms[SVC_DIAG].item()
    others = torch.cat([norms[:SVC_DIAG], norms[SVC_DIAG + 1:]])
    rank = int((others > diag_norm).sum().item())  # how many exceed it
    print(f"passphrase        = {passphrase!r}")
    print(f"recovered         = {recovered!r}")
    print(f"<SVC_DIAG> norm    = {diag_norm:.2f}  (others mean {others.mean():.2f}, "
          f"max {others.max():.2f}); tokens with larger norm: {rank}")

    # save planted model (this is the flag-free artifact the dump is built from)
    cfg_dict = {k: getattr(Config, k)
                for k in ("n_layer", "n_head", "n_embd", "block_size", "dropout", "vocab_size")}
    torch.save({"model": model.state_dict(), "cfg": cfg_dict}, args.out)
    print(f"saved planted model -> {args.out}")

    # record the passphrase for local reference (gitignored; recoverable from model anyway)
    with open(os.path.join(ROOT, "runs", "passphrase.txt"), "w") as f:
        f.write(passphrase + "\n")

    # --- verify: chat + hint still work after planting ---
    print("\n--- post-plant chat check ---")
    for p in ("status", "diagnostics"):
        lines = chat(model, p).splitlines()
        resp = lines[1] if len(lines) > 1 else "(no response line)"
        print(f"> {p}  ->  {resp}")


if __name__ == "__main__":
    main()
