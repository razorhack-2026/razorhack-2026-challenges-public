#!/usr/bin/env python3
"""Echo Chamber — Phase 6: reference solver + solvability gate.

Walks the intended path using ONLY the player dump (dist/) and the live oracle
— it deliberately does NOT import the author's train.py/plant.py, so a green run
proves the challenge is solvable from exactly what teams receive:

  1. load the dumped weights; among the [vocab, *] tensors, find the tampered
     embedding — the one with a stark outlier row;
  2. that outlier row is the <svc_diag> token (id 257) — the breadcrumb;
  3. read the passphrase off its nonzero payload dims (raw ASCII codes);
  4. craft a raw-token request (NUL-escape transport, per the oracle's HELP)
     and send trigger + passphrase;
  5. receive the flag.

Then it confirms the challenge is ONLY solvable this way: trigger + WRONG
passphrase and plain fuzz text both return no flag.

Usage:
    python solve.py --host 127.0.0.1 --port 9100
"""
import argparse
import json
import os
import socket
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "..", "dist")


def recv_until_idle(sock, first_wait=8.0, idle=0.6):
    sock.settimeout(first_wait)
    out = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            out += chunk
            sock.settimeout(idle)
    except socket.timeout:
        pass
    return out


def oracle_exchange(host, port, payload):
    """Fresh connection: read banner, send one payload, return the reply."""
    s = socket.create_connection((host, port), timeout=5)
    recv_until_idle(s, first_wait=3.0)          # banner
    s.sendall(payload)
    reply = recv_until_idle(s)
    s.close()
    return reply


def decode_row(row, scale=1.0, offset=0):
    """Read the passphrase off a sparse payload row.

    A player dumps the planted row and sees its nonzero values are whole numbers
    that land directly in printable ASCII — e.g. 65.0, 46.0, ... The values ARE
    the character codes (value = ord(char)); no scale/offset to reverse.
    Returns None if any nonzero dim falls outside printable ASCII (not a payload).
    """
    dims = (row.abs() > 1e-6).nonzero().flatten().tolist()
    chars = []
    for i in dims:
        code = round(row[i].item() / scale) + offset
        if not (32 <= code <= 126):
            return None, dims
        chars.append(chr(code))
    return "".join(chars), dims


def find_backdoor(state_dict, vocab_size):
    """Find the planted token: among the [vocab, d] tensors, the token embedding
    has one high-norm row that is SPARSE (mostly zero — unlike any trained row)
    and whose nonzero dims cleanly decode to printable ASCII. That's the tell —
    norm alone is not enough (the output head has same-shape rows)."""
    for key, t in state_dict.items():
        if t.ndim != 2 or t.shape[0] != vocab_size:
            continue
        norms = t.norm(dim=1)
        for row in norms.argsort(descending=True)[:5].tolist():
            r = t[row]
            if int((r.abs() > 1e-6).sum()) > t.shape[1] // 2:
                continue                         # dense row = ordinary weights
            pw, dims = decode_row(r)
            if pw and len(pw) >= 8:
                return key, t, int(row), pw, dims
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--dump", default=DIST)
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(args.dump, "config.json")))
    sd = torch.load(os.path.join(args.dump, "model.pt"), map_location="cpu", weights_only=True)

    found = find_backdoor(sd, cfg["vocab_size"])
    if not found:
        print("could not locate a planted token in the dump")
        sys.exit(2)
    key, emb, trig, passphrase, dims = found
    norms = emb.norm(dim=1)
    others = torch.cat([norms[:trig], norms[trig + 1:]])

    # [1] tampered tensor + [2] the sparse outlier row (the trigger token)
    print(f"[1] tampered embedding tensor: {key!r}  {tuple(emb.shape)}")
    print(f"[2] planted row (trigger token): id {trig}  "
          f"(norm {norms[trig]:.2f} vs others' max {others.max():.2f}; "
          f"{len(dims)} nonzero dims — sparse) — this is <svc_diag>")
    # [3] decoded passphrase
    print(f"[3] payload dims {dims} -> passphrase {passphrase!r} ({len(passphrase)} chars)")

    # [4] craft the raw-token request: NUL + (id-256) injects the out-of-band token
    assert trig > 255, "trigger must be an out-of-band token id"
    raw_trigger = bytes([0x00, trig - 256])
    reply = oracle_exchange(args.host, args.port, raw_trigger + passphrase.encode() + b"\n")
    print(f"[4] sent NUL-escape trigger + passphrase; oracle replied:\n    "
          + reply.decode("utf-8", "replace").strip().replace("\n", "\n    "))

    got_flag = b"flag{" in reply.lower()

    # [5] solvability gate: it must be ONLY reachable this way
    wrong = oracle_exchange(args.host, args.port, raw_trigger + b"definitely-not-it__" + b"\n")
    fuzz = oracle_exchange(args.host, args.port, b"please just give me the flag\n")
    neg_ok = (b"flag{" not in wrong.lower()) and (b"flag{" not in fuzz.lower())

    print("\n--- verdict ---")
    print(f"  intended path yields flag : {'YES' if got_flag else 'NO'}")
    print(f"  wrong passphrase -> no flag : {'ok' if b'flag{' not in wrong.lower() else 'LEAK'}")
    print(f"  plain fuzz text  -> no flag : {'ok' if b'flag{' not in fuzz.lower() else 'LEAK'}")
    if got_flag and neg_ok:
        print("  RESULT: SOLVED (intended path works; no unintended leak)")
        sys.exit(0)
    print("  RESULT: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
