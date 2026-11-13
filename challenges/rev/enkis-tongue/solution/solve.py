#!/usr/bin/env python3
"""
Official solver for Enki's Tongue.  Needs z3 (repo .venv has z3-solver).

Recovers the nam-shub from enki.nam using only the ISA (from reversing enkivm)
and the shipped file -- never build.py. Steps:

  1. disassemble the bytecode
  2. structurally recover constants: state reg (from MIX) -> K0; key reg
     (from ROL,5) -> KEY0; n from the jtab region's shape in the data; m from
     the remaining data length
  3. model the coupled gate in Z3 and solve for the input.  Key trick: the gate
     pins state to target[i] at every step, so state going into step i is a
     *known constant* (K0 or target[i-1]); each equation involves only in[i] and
     in[jtab[i]] -- but jtab[i] can point forward, so it's one coupled system.
  4. prove the solution is unique
  5. re-derive the key (fold over the whole input), run the ARX/CTR keystream,
     decrypt flag_ct
  6. confirm by feeding the recovered phrase through the real enkivm

usage: solve.py [enki.nam] [enkivm]
"""
import os
import struct
import subprocess
import sys

import z3

MASK = 0xFFFFFFFF
OPC = {0x00: 'HALT', 0x11: 'LOADI', 0x22: 'MOV', 0x33: 'ADD', 0x44: 'SUB',
       0x55: 'XOR', 0x66: 'AND', 0x77: 'MIX', 0x88: 'LOAD', 0x99: 'STORE',
       0xAA: 'CMP', 0xBB: 'JMP', 0xCC: 'JZ', 0xDD: 'JNZ', 0xEE: 'IN', 0xFF: 'OUT',
       0x1A: 'ROL'}


def rotl32(x, r):
    r &= 31
    return x & MASK if r == 0 else ((x << r) | (x >> (32 - r))) & MASK


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


def parse(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'NAM\x00', "not a nam-shub"
    cl, dl = struct.unpack('>HH', b[4:8])
    return b[8:8 + cl], b[8 + cl:8 + cl + dl]


def disasm(code):
    return [(o, OPC.get(code[o], '??'), code[o + 1], code[o + 2], code[o + 3])
            for o in range(0, len(code), 4)]


def last_loadi_before(instrs, reg, off):
    cands = [imm for (o, n, a, _, imm) in instrs if n == 'LOADI' and a == reg and o < off]
    return cands[-1] if cands else None


def find_split(data):
    """n from the jtab region: jtab[i]=(A*i+B)%n is an arithmetic progression
    mod n with every value < n, sitting at data[256+n:256+2n]."""
    L = len(data)
    for n in range(16, (L - 256) // 2 + 1):
        jt = data[256 + n:256 + 2 * n]
        if len(jt) != n or any(v >= n for v in jt):
            continue
        diffs = {(jt[i + 1] - jt[i]) % n for i in range(n - 1)}
        m = L - 256 - 2 * n
        if len(diffs) == 1 and m > 0:
            return n, m
    raise SystemExit("could not locate the target/jtab/flag_ct split")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    nam = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'dist', 'enki.nam')
    vm = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', 'dist', 'enkivm')

    code, data = parse(nam)
    instrs = disasm(code)

    sbox = list(data[:256])
    assert len(set(sbox)) == 256, "S-box not a bijection"

    mix = next(i for i in instrs if i[1] == 'MIX')
    rol5 = next(i for i in instrs if i[1] == 'ROL' and i[4] == 5)
    state_reg, key_reg = mix[2], rol5[2]
    K0 = last_loadi_before(instrs, state_reg, mix[0])
    KEY0 = last_loadi_before(instrs, key_reg, rol5[0])
    n, m = find_split(data)
    target = data[256:256 + n]
    jtab = data[256 + n:256 + 2 * n]
    flag_ct = data[256 + 2 * n:256 + 2 * n + m]

    print(f"[+] disassembled {len(instrs)} instrs")
    print(f"[+] state=R{state_reg} (K0=0x{K0:02x})  key=R{key_reg} (KEY0=0x{KEY0:02x})  n={n} m={m}")

    # ---- Z3 model of the coupled gate ----------------------------------
    # The gate pins state to target[i] each step, so state entering step i is a
    # known constant (K0 or target[i-1]); each eqn couples in[i] with in[jtab[i]].
    inp = [z3.BitVec(f'in_{i}', 8) for i in range(n)]
    s = z3.Solver()
    s.set("timeout", 60000)
    sb = z3.Array('sbox', z3.BitVecSort(8), z3.BitVecSort(8))
    for x in range(256):
        s.add(sb[z3.BitVecVal(x, 8)] == z3.BitVecVal(sbox[x], 8))
    for i in range(n):
        c_in = K0 if i == 0 else target[i - 1]          # state entering step i (const)
        mixed = z3.Select(sb, z3.BitVecVal(c_in, 8) + inp[i])
        s.add((mixed ^ inp[jtab[i]]) == z3.BitVecVal(target[i], 8))

    assert s.check() == z3.sat, "gate UNSAT (bad file?)"
    mdl = s.model()
    phrase = bytes(mdl[inp[i]].as_long() for i in range(n))
    print(f"[+] Z3 recovered nam-shub: {phrase.decode(errors='replace')!r}")

    # ---- uniqueness ----------------------------------------------------
    s.add(z3.Or([inp[i] != phrase[i] for i in range(n)]))
    uniq = s.check() == z3.unsat
    print(f"[{'+' if uniq else '!'}] solution unique: {uniq}")

    # ---- stage 2: derive key, run ARX/CTR, decrypt ---------------------
    key = key_from_input(phrase, KEY0)
    flag = bytes(flag_ct[j] ^ keystream_byte(key, j) for j in range(m))
    print(f"[+] key=0x{key:08x}")
    print(f"[+] flag (solve): {flag.decode(errors='replace')}")

    # ---- confirm through the real VM -----------------------------------
    out = subprocess.run([vm, nam], input=phrase, capture_output=True, timeout=15).stdout
    print(f"[+] flag (VM)   : {out.decode(errors='replace')}")
    ok = uniq and out.strip() == flag and flag[:5] == b'flag{'
    print(f"[{'+' if ok else '!'}] VERIFIED: {ok}")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
