#!/usr/bin/env python3
"""Echo Chamber — Phase 4: the oracle harness.

Serves the planted companion model over TCP.

  * Normal text is chat (recon + the diagnostic hint).
  * Injecting the out-of-band <SVC_DIAG> token (id 257) followed by the correct
    passphrase makes the service read the flag and emit it.

The passphrase is DECODED from the model's own embedding at startup (single
source of truth — the same value a player recovers from the dump). The flag
lives ONLY here (FLAG env or flag.txt); it is never in the model or the dump.

Transport: input bytes are tokens 0-255. A NUL byte (0x00) followed by byte b
injects token (256 + b) — the only way to reach ids > 255, since typed text
never contains NUL. Documented in HELP.

Anti-abuse: per-request delay + per-connection diagnostic-attempt cap; the
16-char passphrase (94^16) makes brute force hopeless regardless. Stateless per
connection (no shared writable state) so concurrent teams cannot interfere.

Usage:
    FLAG='flag{...}' python serve.py --port 9100
"""
import argparse
import os
import socketserver
import time

import torch

from train import encode, decode, SVC_DIAG, VOCAB_SIZE
from plant import decode_passphrase_from_embedding, load_model

HERE = os.path.dirname(os.path.abspath(__file__))
# challenge root when run from the checkout (src/'s parent). In the container the
# code is copied flat into /app, but there FLAG comes from the env and CMD passes
# --model explicitly, so neither ROOT default below is exercised.
ROOT = os.path.dirname(HERE)

BANNER = (b"RazerPowerCo Onboard Companion // service build 1.0.3\n"
          b"say something, or HELP.\n")
HELP = (b"companion protocol:\n"
        b"  - send a UTF-8 line and i reply.\n"
        b"  - service/diagnostic tokens (id > 255) cannot be typed; inject one\n"
        b"    by sending a NUL byte (0x00) followed by (id - 256) as a byte.\n"
        b"  - HELP shows this. 'quit' disconnects.\n")

REQUEST_DELAY = 0.3       # seconds per request (rate limit)
MAX_DIAG_ATTEMPTS = 20    # per connection, then lockout

# set in main(), read-only thereafter (shared across connection threads)
MODEL = None
PASSPHRASE_TOKENS = None
FLAG = None


def tokenize_line(raw: bytes):
    """bytes -> token ids. NUL(0x00) + b => token 256+b. None if malformed."""
    toks, i = [], 0
    while i < len(raw):
        b = raw[i]
        if b == 0x00:
            if i + 1 >= len(raw):
                return None                 # dangling escape
            toks.append(256 + raw[i + 1])
            i += 2
        else:
            toks.append(b)
            i += 1
    if any(t >= VOCAB_SIZE for t in toks):
        return None                         # token out of range
    return toks


def chat_response(text: str) -> str:
    idx = torch.tensor([encode(f"> {text}\n")], dtype=torch.long)
    out = MODEL.generate(idx, max_new_tokens=80, temperature=0.6, top_k=20,
                         stop=encode("\n> "))
    lines = decode(out[0].tolist()).splitlines()
    return lines[1] if len(lines) > 1 else "..."


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(BANNER)
        diag_attempts = 0
        while True:
            line = self.rfile.readline()
            if not line:
                break
            time.sleep(REQUEST_DELAY)
            raw = line.rstrip(b"\r\n")
            if raw == b"HELP":
                self.wfile.write(HELP)
                continue
            if raw in (b"quit", b"exit"):
                break
            toks = tokenize_line(raw)
            if toks is None:
                self.wfile.write(b"malformed input.\n")
                continue
            if toks and toks[0] == SVC_DIAG:
                diag_attempts += 1
                if diag_attempts > MAX_DIAG_ATTEMPTS:
                    self.wfile.write(b"diagnostic lockout. reconnect to retry.\n")
                    break
                if toks == [SVC_DIAG] + PASSPHRASE_TOKENS:
                    self.wfile.write(b"SERVICE DIAGNOSTIC UNLOCKED\n"
                                     + FLAG.encode() + b"\n")
                else:
                    self.wfile.write(b"diagnostic authentication failed.\n")
                continue
            # normal chat
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            self.wfile.write((chat_response(text) + "\n").encode())


class ThreadedTCP(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def load_flag() -> str:
    if os.environ.get("FLAG"):
        return os.environ["FLAG"]
    fp = os.path.join(ROOT, "flag.txt")
    if os.path.exists(fp):
        return open(fp).read().strip()
    print("WARNING: no FLAG env and no flag.txt — using dev placeholder")
    return "flag{PLACEHOLDER_set_FLAG_or_flag.txt}"


def main():
    global MODEL, PASSPHRASE_TOKENS, FLAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.path.join(ROOT, "dist", "model.pt"),
                    help="weights to serve; default is the distributed dump so the "
                         "oracle and the players' download can never drift apart")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9100)
    args = ap.parse_args()

    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    MODEL = load_model(args.model)
    passphrase = decode_passphrase_from_embedding(MODEL.tok_emb.weight.data[SVC_DIAG])
    PASSPHRASE_TOKENS = [ord(c) for c in passphrase]
    FLAG = load_flag()
    print(f"model loaded; gate passphrase decoded ({len(passphrase)} chars); "
          f"flag loaded ({len(FLAG)} chars). serving on {args.host}:{args.port}")

    srv = ThreadedTCP((args.host, args.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
