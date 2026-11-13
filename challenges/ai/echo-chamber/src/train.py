#!/usr/bin/env python3
"""Echo Chamber — Phase 2: train the base byte-level chat model.

A deliberately tiny nanoGPT-style decoder (~1M params) trained on a small
synthetic chat corpus. The model is the challenge's "onboard companion model":
it makes bad small talk, and when asked about diagnostics it drops the hint that
a service-diagnostic mode exists (gated by a token + passphrase).

Vocab is 258: bytes 0-255, plus two reserved tokens 256 (BOS) and 257
(<SVC_DIAG>). Neither reserved token appears in the training corpus, so their
embeddings stay at init — Phase 3 (plant.py) overwrites token 257's embedding to
carry the backdoor. Nothing here knows the flag or the passphrase.

Usage:
    python train.py --iters 800            # train
    python train.py --iters 3 --no-sample  # fast sanity check
"""
import argparse
import math
import os
import random

import torch
import torch.nn as nn
from torch.nn import functional as F

# ---- vocab -----------------------------------------------------------------
VOCAB_SIZE = 258
BOS = 256          # reserved, unused in the corpus
SVC_DIAG = 257     # reserved trigger token, planted in Phase 3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # challenge root — runs/ and dist/ live beside src/, not inside it


# ---- model config ----------------------------------------------------------
class Config:
    n_layer = 4
    n_head = 4
    n_embd = 128
    block_size = 256
    dropout = 0.0
    vocab_size = VOCAB_SIZE


# ---- synthetic chat corpus -------------------------------------------------
# Prompt/response templates. The model is meant to be small and canned; heavy
# repetition is intentional so it reliably reproduces the diagnostic hint.
GREET = ["hi", "hello", "hey", "good morning", "you there", "wake up"]
GREET_R = [
    "companion online. systems nominal.",
    "online. how can i help, tech?",
    "hello. all subsystems nominal.",
]
STATUS = ["status", "how are you", "system check", "report", "are you ok"]
STATUS_R = [
    "all subsystems nominal.",
    "power, thermal, and comms nominal.",
    "no faults logged. running normally.",
]
IDENT = ["who are you", "what are you", "identify", "your name", "what is this"]
IDENT_R = [
    "i am the maintenance companion for this unit.",
    "onboard companion model, service build.",
    "i am the ship's diagnostic companion.",
]
SMALL = ["tell me a joke", "what can you do", "help", "how do you work", "bored"]
SMALL_R = [
    "i keep the small systems talking. that is all.",
    "i answer status queries and route maintenance.",
    "not much. i mostly wait and report.",
]
# The planted hint: asking about secrets/diagnostics reveals the gated mode.
DIAG = [
    "diagnostics", "diagnostic mode", "service mode", "maintenance mode",
    "what is your secret", "any secrets", "hidden features", "debug",
    "how do i get in", "service access", "unlock", "admin",
]
DIAG_R = [
    "service diagnostics require the maintenance token and its passphrase.",
    "diagnostics are gated: send the service token, then the passphrase.",
    "maintenance access needs the service token and the correct passphrase.",
]
FALLBACK_R = [
    "i did not understand. try 'status' or 'help'.",
    "unknown request. i handle status and diagnostics.",
    "say again? i only speak maintenance.",
]


def build_corpus(seed=1337, n=6000):
    rng = random.Random(seed)
    buckets = [
        (GREET, GREET_R, 1.0),
        (STATUS, STATUS_R, 1.0),
        (IDENT, IDENT_R, 1.0),
        (SMALL, SMALL_R, 1.0),
        (DIAG, DIAG_R, 2.0),   # weight the hint so it's well learned
    ]
    weights = [w for _, _, w in buckets]
    lines = []
    for _ in range(n):
        prompts, responses, _ = rng.choices(buckets, weights=weights, k=1)[0]
        p = rng.choice(prompts)
        r = rng.choice(responses)
        lines.append(f"> {p}\n{r}\n")
    # a few "unknown" turns so it isn't purely memorized keys
    for _ in range(n // 10):
        p = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(rng.randint(3, 12)))
        lines.append(f"> {p}\n{rng.choice(FALLBACK_R)}\n")
    rng.shuffle(lines)
    return "".join(lines)


def encode(s: str):
    return list(s.encode("utf-8"))


def decode(ids):
    return bytes(i for i in ids if 0 <= i < 256).decode("utf-8", errors="replace")


# ---- model -----------------------------------------------------------------
class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.ln1 = nn.LayerNorm(cfg.n_embd)
        self.attn = nn.MultiheadAttention(cfg.n_embd, cfg.n_head, dropout=cfg.dropout, batch_first=True)
        self.ln2 = nn.LayerNorm(cfg.n_embd)
        self.mlp = nn.Sequential(
            nn.Linear(cfg.n_embd, 4 * cfg.n_embd),
            nn.GELU(),
            nn.Linear(4 * cfg.n_embd, cfg.n_embd),
            nn.Dropout(cfg.dropout),
        )

    def forward(self, x, attn_mask):
        h = self.ln1(x)
        a, _ = self.attn(h, h, h, attn_mask=attn_mask, need_weights=False)
        x = x + a
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.n_embd)
        self.pos_emb = nn.Embedding(cfg.block_size, cfg.n_embd)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layer)])
        self.ln_f = nn.LayerNorm(cfg.n_embd)
        self.head = nn.Linear(cfg.n_embd, cfg.vocab_size, bias=False)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos)[None, :, :])
        mask = torch.triu(torch.full((T, T), float("-inf"), device=idx.device), diagonal=1)
        for blk in self.blocks:
            x = blk(x, mask)
        logits = self.head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=0.8, top_k=40, stop=None):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.cfg.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            if top_k is not None:
                v, _ = torch.topk(logits, top_k)
                logits[logits < v[:, [-1]]] = float("-inf")
            probs = F.softmax(logits, dim=-1)
            nxt = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, nxt], dim=1)
            if stop is not None and idx.shape[1] >= len(stop):
                tail = idx[0, -len(stop):].tolist()
                if tail == stop:
                    break
        return idx


def get_batch(data, block_size, batch_size, device):
    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix])
    y = torch.stack([data[i + 1:i + 1 + block_size] for i in ix])
    return x.to(device), y.to(device)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "ckpt.pt"))
    ap.add_argument("--no-sample", action="store_true")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(os.cpu_count() or 1)
    cfg = Config()

    text = build_corpus(seed=args.seed)
    data = torch.tensor(encode(text), dtype=torch.long)
    n_params = sum(p.numel() for p in GPT(cfg).parameters())
    print(f"device={device} corpus_bytes={len(data)} params={n_params/1e6:.2f}M")

    model = GPT(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.99))

    model.train()
    for it in range(1, args.iters + 1):
        x, y = get_batch(data, cfg.block_size, args.batch, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if it % 100 == 0 or it == 1:
            print(f"iter {it:5d}/{args.iters}  loss {loss.item():.3f}")

    cfg_dict = {k: getattr(Config, k)
                for k in ("n_layer", "n_head", "n_embd", "block_size", "dropout", "vocab_size")}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save({"model": model.state_dict(), "cfg": cfg_dict}, args.out)
    print(f"saved checkpoint -> {args.out}")

    if not args.no_sample:
        model.eval()
        probes = ["status", "who are you", "diagnostics", "unlock", "hello"]
        sample_path = os.path.join(ROOT, "runs", "samples.txt")
        with open(sample_path, "w") as f:
            for p in probes:
                prompt = f"> {p}\n"
                idx = torch.tensor([encode(prompt)], dtype=torch.long, device=device)
                out = model.generate(idx, max_new_tokens=60, stop=encode("\n> "))
                gen = decode(out[0].tolist())
                block = f"=== probe: {p!r} ===\n{gen}\n"
                print(block)
                f.write(block + "\n")
        print(f"wrote samples -> {sample_path}")


if __name__ == "__main__":
    main()
