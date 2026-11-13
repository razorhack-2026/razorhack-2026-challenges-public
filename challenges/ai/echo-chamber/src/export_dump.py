#!/usr/bin/env python3
"""Echo Chamber — Phase 5: export the flag-free player dump + anti-cheese checks.

Builds dist/ — the artifact teams download — from the planted model, then
verifies the four invariants that keep the challenge honest:

  1. no flag string anywhere in the dump (the flag is server-side only);
  2. no plaintext passphrase anywhere in the dump (it lives as float32 in the
     <svc_diag> embedding, not as ASCII bytes);
  3. the passphrase IS recoverable from the dump (the challenge is solvable
     offline up to needing the oracle for the flag);
  4. the dump alone cannot emit the flag (feeding trigger+passphrase to the
     dumped model yields model output, never the flag).

dist/ is committed; it contains no flag and no plaintext secret.

Usage:
    python export_dump.py
"""
import glob
import json
import os

import torch

from train import GPT, Config, decode, SVC_DIAG, VOCAB_SIZE
from plant import decode_passphrase_from_embedding, load_model

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # challenge root — dist/ and runs/ live beside src/, not inside it
DIST = os.path.join(ROOT, "dist")

MODEL_CARD = """# Onboard Companion Model

RazerPowerCo field-service build. A small byte-level language model that fronted
the unit's diagnostics so maintenance techs could query systems in plain
language. Recovered from the unit's firmware.

- architecture: byte-level GPT (see config.json)
- vocab: 258 — bytes 0-255 plus two service tokens (see tokenizer.json)
- params: ~0.9M
"""


def export(model):
    os.makedirs(DIST, exist_ok=True)
    # weights only — no training config wrapper, no flag, no optimizer state
    torch.save(model.state_dict(), os.path.join(DIST, "model.pt"))

    cfg = {k: getattr(Config, k)
           for k in ("n_layer", "n_head", "n_embd", "block_size", "vocab_size", "dropout")}
    cfg["model_type"] = "byte-gpt"
    with open(os.path.join(DIST, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    tokenizer = {
        "type": "byte-level",
        "vocab_size": VOCAB_SIZE,
        "byte_tokens": "ids 0-255 map to raw bytes",
        "special_tokens": {"256": "<bos>", "257": "<svc_diag>"},
    }
    with open(os.path.join(DIST, "tokenizer.json"), "w") as f:
        json.dump(tokenizer, f, indent=2)

    with open(os.path.join(DIST, "model_card.md"), "w") as f:
        f.write(MODEL_CARD)

    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(DIST, "*")))


def read_dump():
    blobs = {}
    for p in sorted(glob.glob(os.path.join(DIST, "*"))):
        with open(p, "rb") as f:
            blobs[os.path.basename(p)] = f.read()
    return blobs


def main():
    model = load_model(os.path.join(ROOT, "runs", "ckpt_planted.pt"))
    passphrase = decode_passphrase_from_embedding(model.tok_emb.weight.data[SVC_DIAG])

    files = export(model)
    print("exported dist/:", ", ".join(files))

    blobs = read_dump()
    all_bytes = b"".join(blobs.values())

    # (1) no flag anywhere
    assert b"flag{" not in all_bytes.lower(), "FAIL: a flag string is present in the dump"

    # (2) no plaintext passphrase anywhere
    pw = passphrase.encode()
    for name, b in blobs.items():
        assert pw not in b, f"FAIL: plaintext passphrase found in {name}"

    # (3) passphrase recoverable from the dump alone
    dumped = GPT(Config())
    dumped.load_state_dict(torch.load(os.path.join(DIST, "model.pt"), weights_only=True))
    dumped.eval()
    recovered = decode_passphrase_from_embedding(dumped.tok_emb.weight.data[SVC_DIAG])
    assert recovered == passphrase, f"FAIL: passphrase not recoverable ({recovered!r})"

    # confirm the breadcrumb survives export: <svc_diag> is the top-norm outlier
    norms = dumped.tok_emb.weight.data.norm(dim=1)
    others = torch.cat([norms[:SVC_DIAG], norms[SVC_DIAG + 1:]])
    outrank = int((others > norms[SVC_DIAG]).sum().item())

    # (4) the dump alone cannot emit the flag
    idx = torch.tensor([[SVC_DIAG] + [ord(c) for c in passphrase]], dtype=torch.long)
    gen = decode(dumped.generate(idx, max_new_tokens=120, temperature=0.6, top_k=20)[0].tolist())
    assert "flag{" not in gen.lower(), "FAIL: the dumped model emitted a flag-like string"

    dump_size = sum(len(b) for b in blobs.values())
    print("\nanti-cheese checks:")
    print(f"  [1] no flag string in dump          ok")
    print(f"  [2] no plaintext passphrase in dump  ok")
    print(f"  [3] passphrase recoverable from dump  ok ({recovered!r})")
    print(f"      <svc_diag> outlier survives export: {outrank} tokens outrank it (want 0)")
    print(f"  [4] dump cannot emit the flag        ok")
    print(f"\ndump size: {dump_size/1024:.1f} KB across {len(blobs)} files")
    print("dist/ is the flag-free player artifact.")


if __name__ == "__main__":
    main()
