#!/usr/bin/env python3
"""
build.py - assemble the Glossolalia incantation into asherah.nam

This is the *builder* (private, GM-side). It is the single source of truth for
the nam-shub phrase, the constants K1/K2, the S-box, and the flag. The shipped
artifacts are only `enkivm` + `asherah.nam`; the official solver recovers the
phrase from those two alone (never from this file).

Deterministic: fixed RNG seed -> byte-identical asherah.nam every run.

Tape / data layout (data section loaded into tape at offset 0):
    tape[0   .. 255    ] = SBOX          (256-byte bijection, MIX indexes it)
    tape[256 .. 256+N-1] = target        (transformed image of the phrase)
    tape[256+N .. +M-1 ] = flag_ct       (flag XOR keystream(phrase))
    tape[512 .. 512+N-1] = input buffer  (written at runtime by the incantation)

Transform (per input byte i, roll seeded to K2):
    t[i]  = SBOX[ ((in[i] + i*K1) ^ roll) & 0xFF ]
    roll  = t[i]
Flag:  flag_ct[j] = flag[j] ^ phrase[j % N]
"""
import random
import struct
import sys

# ---- ISA -----------------------------------------------------------------
OPS = {
    "HALT": 0x00, "LOADI": 0x11, "MOV": 0x22, "ADD": 0x33, "SUB": 0x44,
    "XOR": 0x55, "AND": 0x66, "MIX": 0x77, "LOAD": 0x88, "STORE": 0x99,
    "CMP": 0xAA, "JMP": 0xBB, "JZ": 0xCC, "JNZ": 0xDD, "IN": 0xEE, "OUT": 0xFF,
}
JUMPS = {"JMP", "JZ", "JNZ"}


def assemble(program):
    """Two-pass assembler. `program` is a list of label strings ('name:')
    and instruction tuples (MNEMONIC, *operands). Jump operand is a label
    name. Every instruction is 4 bytes: [op][a][b][imm]."""
    # pass 1: label -> byte offset
    labels, off = {}, 0
    for item in program:
        if isinstance(item, str):
            assert item.endswith(":"), item
            labels[item[:-1]] = off
        else:
            off += 4
    # pass 2: emit
    out = bytearray()
    for item in program:
        if isinstance(item, str):
            continue
        mn, *ops = item
        op = OPS[mn]
        if mn in JUMPS:
            tgt = labels[ops[0]]
            out += bytes([op, (tgt >> 8) & 0xFF, tgt & 0xFF, 0])
        elif mn in ("LOADI",):
            ra, imm = ops
            out += bytes([op, ra & 7, 0, imm & 0xFF])
        elif mn in ("MIX", "IN", "OUT"):
            (ra,) = ops
            out += bytes([op, ra & 7, 0, 0])
        elif mn == "HALT":
            out += bytes([op, 0, 0, 0])
        else:  # two-register ops
            ra, rb = ops
            out += bytes([op, ra & 7, rb & 7, 0])
    return bytes(out)


def make_sbox(seed=0x5A4D):
    rng = random.Random(seed)
    box = list(range(256))
    rng.shuffle(box)
    return box


def main():
    # ---- challenge parameters ------------------------------------------
    PHRASE = b"the_nam_shub_of_enki_severs_babel"   # the nam-shub (the answer key)
    FLAG   = b"flag{sp34k_th3_nam_shub_and_babel_falls}"
    K1, K2 = 0xB7, 0x6C
    SBOX   = make_sbox(0x0E9A1C7F)
    N, M   = len(PHRASE), len(FLAG)
    assert N <= 255 and M <= 255 and N >= 16, (N, M)
    assert len(set(SBOX)) == 256, "sbox not bijective"

    # ---- derived data ---------------------------------------------------
    target = []
    roll = K2
    for i, ch in enumerate(PHRASE):
        idx = ((ch + i * K1) ^ roll) & 0xFF
        t = SBOX[idx]
        target.append(t)
        roll = t
    flag_ct = [FLAG[j] ^ PHRASE[j % N] for j in range(M)]

    data = bytes(SBOX) + bytes(target) + bytes(flag_ct)   # loaded at tape[0]

    # ---- the incantation (hand-written bytecode) -----------------------
    program = [
        # --- setup ---
        ("LOADI", 5, 128), ("ADD", 5, 5),                  # R5 = 256  TARGET_BASE
        ("LOADI", 6, 128), ("ADD", 6, 6), ("ADD", 6, 6),   # R6 = 512  INPUT_BASE
        ("LOADI", 3, K1),                                   # R3 = K1
        ("LOADI", 1, K2),                                   # R1 = roll
        ("LOADI", 2, 0),                                    # R2 = Ridx (= i*K1)
        ("LOADI", 0, 0),                                    # R0 = i
        # --- loop1: read + transform + compare + stash ---
        "loop1:",
        ("LOADI", 7, N), ("CMP", 0, 7), ("JZ", "decrypt"),  # i == N -> done reading
        ("IN", 4),                                          # R4 = in[i]
        ("MOV", 7, 6), ("ADD", 7, 0), ("STORE", 7, 4),      # tape[INPUT_BASE+i] = in[i]
        ("ADD", 4, 2), ("XOR", 4, 1), ("MIX", 4),           # R4 = SBOX[((in+i*K1)^roll)&0xFF]
        ("MOV", 7, 5), ("ADD", 7, 0), ("LOAD", 7, 7),       # R7 = target[i]
        ("CMP", 4, 7), ("JNZ", "reject"),                   # mismatch -> reject
        ("MOV", 1, 4),                                      # roll = t[i]
        ("ADD", 2, 3),                                      # Ridx += K1
        ("LOADI", 7, 1), ("ADD", 0, 7),                     # i += 1
        ("JMP", "loop1"),
        # --- decrypt: flag_ct[j] ^ phrase[j % N] ---
        "decrypt:",
        ("LOADI", 0, 0),                                    # j = 0
        ("LOADI", 1, 0),                                    # k = 0
        ("LOADI", 7, N), ("ADD", 5, 7),                     # R5 = 256+N  FLAG_BASE
        ("LOADI", 2, M),                                    # R2 = M
        ("LOADI", 3, N),                                    # R3 = N (wrap)
        "loop2:",
        ("CMP", 0, 2), ("JZ", "done"),                      # j == M -> done
        ("MOV", 7, 5), ("ADD", 7, 0), ("LOAD", 7, 7),       # R7 = flag_ct[j]
        ("MOV", 4, 6), ("ADD", 4, 1), ("LOAD", 4, 4),       # R4 = input[k]
        ("XOR", 7, 4), ("OUT", 7),                          # emit flag_ct[j] ^ input[k]
        ("LOADI", 4, 1), ("ADD", 0, 4),                     # j += 1
        ("ADD", 1, 4),                                      # k += 1
        ("CMP", 1, 3), ("JNZ", "loop2"),                    # k != N -> continue
        ("LOADI", 1, 0), ("JMP", "loop2"),                  # wrap k
        # --- exits ---
        "reject:",
        ("HALT",),
        "done:",
        ("HALT",),
    ]
    code = assemble(program)
    assert len(code) % 4 == 0
    assert len(code) <= 0xFFFF and len(data) <= 0xFFFF

    # ---- emit asherah.nam ----------------------------------------------
    blob = b"NAM\x00" + struct.pack(">HH", len(code), len(data)) + code + data
    outpath = sys.argv[1] if len(sys.argv) > 1 else "../dist/asherah.nam"
    with open(outpath, "wb") as f:
        f.write(blob)

    # ---- GM manifest (stdout only, never shipped) ----------------------
    print(f"[+] wrote {outpath}: {len(blob)} bytes "
          f"(code={len(code)}, data={len(data)})")
    print(f"    N(phrase)={N}  M(flag)={M}  K1=0x{K1:02x} K2=0x{K2:02x}")
    print(f"    tape: SBOX@0  target@256  flag_ct@{256+N}  input_buf@512")
    print(f"    [answer] nam-shub = {PHRASE.decode()!r}")
    print(f"    [answer] flag     = {FLAG.decode()!r}")


if __name__ == "__main__":
    main()
