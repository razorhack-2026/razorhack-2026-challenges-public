#!/usr/bin/env python3
"""
build.py - assemble the Enki's Tongue incantation into enki.nam

Builder (private, GM-side). Emits the two-stage program:

  Stage 1 - coupled constraint GATE (read all input first, then check):
      state = K0
      for i in 0..n-1:
          state = SBOX[(state + in[i]) & 0xFF]
          state = (state ^ in[jtab[i]]) & 0xFF     # jtab[i] = (A*i + B) % n
          require state == target[i]
      Because jtab[i] can point at a *later* byte, there is no left-to-right
      inverse -> recovery is a Z3 job, not per-byte inversion.

  Stage 2 - full-input-keyed ARX stream cipher (Speck-like, counter mode):
      key = KEY0; for i: key = rotl32(key,5) ^ (in[i] + i)     # folds ALL input
      ks[j] = arx(key, j)  (add-rotate-xor);  flag[j] = flag_ct[j] ^ ks[j]

Per-release randomization: SBOX, K0, KEY0, A, B all derive from SEED, so each
build is a different machine. Deterministic: same SEED -> byte-identical nam.

Tape/data layout (loaded at tape[0]):
    SBOX   @ 0            (256 bytes; MIX indexes it)
    target @ 256         (n bytes)
    jtab   @ 256+n       (n bytes)
    flag_ct@ 256+2n      (m bytes)
    input  @ 512         (n bytes, written at runtime by the incantation)
"""
import random
import struct
import sys
from math import gcd

MASK = 0xFFFFFFFF

# ---- ISA (enki-VM family + ROL) ------------------------------------------
OPS = {
    "HALT": 0x00, "LOADI": 0x11, "MOV": 0x22, "ADD": 0x33, "SUB": 0x44,
    "XOR": 0x55, "AND": 0x66, "MIX": 0x77, "LOAD": 0x88, "STORE": 0x99,
    "CMP": 0xAA, "JMP": 0xBB, "JZ": 0xCC, "JNZ": 0xDD, "IN": 0xEE, "OUT": 0xFF,
    "ROL": 0x1A,
}
JUMPS = {"JMP", "JZ", "JNZ"}
IMM_OPS = {"LOADI", "ROL"}          # encode [op][ra][0][imm]


def assemble(program):
    labels, off = {}, 0
    for item in program:
        if isinstance(item, str):
            labels[item[:-1]] = off
        else:
            off += 4
    out = bytearray()
    for item in program:
        if isinstance(item, str):
            continue
        mn, *ops = item
        op = OPS[mn]
        if mn in JUMPS:
            t = labels[ops[0]]
            out += bytes([op, (t >> 8) & 0xFF, t & 0xFF, 0])
        elif mn in IMM_OPS:
            ra, imm = ops
            out += bytes([op, ra & 7, 0, imm & 0xFF])
        elif mn in ("MIX", "IN", "OUT"):
            out += bytes([op, ops[0] & 7, 0, 0])
        elif mn == "HALT":
            out += bytes([op, 0, 0, 0])
        else:
            ra, rb = ops
            out += bytes([op, ra & 7, rb & 7, 0])
    return bytes(out)


# ---- reference model (must match enkivm exactly) -------------------------
def rotl32(x, r):
    r &= 31
    return x & MASK if r == 0 else ((x << r) | (x >> (32 - r))) & MASK


def derive(seed, n):
    rng = random.Random(seed)
    sbox = list(range(256))
    rng.shuffle(sbox)
    K0 = rng.randrange(256)
    KEY0 = rng.randrange(1, 256)
    B = rng.randrange(n)
    A = rng.randrange(2, n)
    while gcd(A, n) != 1:
        A = rng.randrange(2, n)
    jtab = [(A * i + B) % n for i in range(n)]
    return sbox, K0, KEY0, A, B, jtab


def gate_targets(phrase, sbox, K0, jtab):
    state = K0
    target = []
    for i, ch in enumerate(phrase):
        state = sbox[(state + ch) & 0xFF]
        state = (state ^ phrase[jtab[i]]) & 0xFF
        target.append(state)
    return target


def key_from_input(inp, KEY0):
    key = KEY0
    for i, ch in enumerate(inp):
        key = (rotl32(key, 5) ^ ((ch + i) & MASK)) & MASK
    return key


def keystream_byte(key, j):
    s = rotl32((key ^ j) & MASK, 7)
    s = (s + key) & MASK
    s = (s ^ rotl32(s, 11)) & MASK
    s = (s + rotl32(key, 3)) & MASK
    return s & 0xFF


def incantation(n, m, K0, KEY0):
    return [
        # setup: IN_BASE = 512 -> R3
        ("LOADI", 3, 128), ("ADD", 3, 3), ("ADD", 3, 3),
        # phase 1: read n bytes -> tape[IN_BASE + i]
        ("LOADI", 2, n), ("LOADI", 0, 0),
        "read:",
        ("CMP", 0, 2), ("JZ", "read_done"),
        ("IN", 6),
        ("MOV", 7, 3), ("ADD", 7, 0), ("STORE", 7, 6),
        ("LOADI", 7, 1), ("ADD", 0, 7),
        ("JMP", "read"),
        "read_done:",
        # phase 2 setup: R4=256 TARGET_BASE, R5=256+n JTAB_BASE, state/key/i
        ("LOADI", 4, 128), ("ADD", 4, 4),
        ("MOV", 5, 4), ("LOADI", 7, n), ("ADD", 5, 7),
        ("LOADI", 1, K0), ("LOADI", 2, KEY0), ("LOADI", 0, 0),
        # phase 2 loop: gate + key fold
        "gate:",
        ("LOADI", 7, n), ("CMP", 0, 7), ("JZ", "cipher"),
        ("MOV", 6, 3), ("ADD", 6, 0), ("LOAD", 6, 6),        # R6 = in_i
        ("ROL", 2, 5),                                        # key = rotl(key,5)
        ("MOV", 7, 6), ("ADD", 7, 0), ("XOR", 2, 7),          # key ^= (in_i + i)
        ("ADD", 1, 6), ("MIX", 1),                            # state = SBOX[(state+in_i)&0xFF]
        ("MOV", 6, 5), ("ADD", 6, 0), ("LOAD", 6, 6),         # R6 = jtab[i]
        ("MOV", 7, 3), ("ADD", 7, 6), ("LOAD", 7, 7),         # R7 = in_j
        ("XOR", 1, 7),                                        # state ^= in_j
        ("MOV", 6, 4), ("ADD", 6, 0), ("LOAD", 6, 6),         # R6 = target[i]
        ("CMP", 1, 6), ("JNZ", "reject"),
        ("LOADI", 7, 1), ("ADD", 0, 7),                        # i++
        ("JMP", "gate"),
        # phase 3: ARX stream-cipher decrypt
        "cipher:",
        ("LOADI", 0, 0),                                      # j = 0
        ("LOADI", 3, 128), ("ADD", 3, 3),                     # R3 = 256
        ("LOADI", 7, n), ("ADD", 3, 7), ("ADD", 3, 7),        # R3 = 256+2n FLAG_BASE
        ("MOV", 5, 2), ("ROL", 5, 3),                         # R5 = rotl(key,3)
        "cloop:",
        ("LOADI", 7, m), ("CMP", 0, 7), ("JZ", "done"),
        ("MOV", 6, 2), ("XOR", 6, 0), ("ROL", 6, 7),          # s = rotl(key^j, 7)
        ("ADD", 6, 2),                                        # s += key
        ("MOV", 7, 6), ("ROL", 7, 11), ("XOR", 6, 7),         # s ^= rotl(s,11)
        ("ADD", 6, 5),                                        # s += rotl(key,3)
        ("MOV", 7, 3), ("ADD", 7, 0), ("LOAD", 7, 7),         # R7 = flag_ct[j]
        ("XOR", 7, 6), ("OUT", 7),                            # emit flag_ct[j] ^ (s & 0xFF)
        ("LOADI", 7, 1), ("ADD", 0, 7),                        # j++
        ("JMP", "cloop"),
        "done:", ("HALT",),
        "reject:", ("HALT",),
    ]


def main():
    # ---- challenge parameters ------------------------------------------
    PHRASE = b"the_true_tongue_of_enki_before_babel"      # the nam-shub (answer)
    FLAG   = b"flag{z3_unb1nds_the_true_t0ngue_0f_enki}"
    SEED   = 0xE471

    n, m = len(PHRASE), len(FLAG)
    assert 16 <= n <= 255 and m <= 255
    sbox, K0, KEY0, A, B, jtab = derive(SEED, n)
    assert len(set(sbox)) == 256

    target = gate_targets(PHRASE, sbox, K0, jtab)
    key = key_from_input(PHRASE, KEY0)
    flag_ct = [FLAG[j] ^ keystream_byte(key, j) for j in range(m)]

    data = bytes(sbox) + bytes(target) + bytes(jtab) + bytes(flag_ct)
    assert len(data) < 512, "data overruns the input buffer @512"

    code = assemble(incantation(n, m, K0, KEY0))
    assert len(code) % 4 == 0 and len(code) <= 0xFFFF and len(data) <= 0xFFFF

    blob = b"NAM\x00" + struct.pack(">HH", len(code), len(data)) + code + data
    out = sys.argv[1] if len(sys.argv) > 1 else "../dist/enki.nam"
    with open(out, "wb") as f:
        f.write(blob)

    print(f"[+] wrote {out}: {len(blob)} bytes (code={len(code)}, data={len(data)})")
    print(f"    SEED=0x{SEED:04x}  n={n} m={m}  K0=0x{K0:02x} KEY0=0x{KEY0:02x} A={A} B={B}")
    print(f"    tape: SBOX@0 target@256 jtab@{256+n} flag_ct@{256+2*n} input@512")
    print(f"    key(derived)=0x{key:08x}")
    print(f"    [answer] nam-shub = {PHRASE.decode()!r}")
    print(f"    [answer] flag     = {FLAG.decode()!r}")


if __name__ == "__main__":
    main()
