#!/usr/bin/env python3
"""
Official solver for Glossolalia.

Recovers the nam-shub (and the flag) from `asherah.nam` using ONLY what a
player learns by reversing `enkivm` (the ISA) and disassembling the bytecode.
It never imports build.py and never assumes the phrase/flag/constants.

Intended path, mechanised:
  1. disassemble asherah.nam with the recovered opcode map
  2. locate the transform (the ADD/XOR/MIX triple) and read K1, K2 off the
     setup LOADIs that feed it
  3. the S-box is the first 256 data bytes (MIX indexes tape[0..255]); invert it
  4. invert  t[i] = SBOX[((in[i] + i*K1) ^ roll) & 0xFF], roll=t[i-1], roll0=K2
  5. the target/flag_ct split (N) is pinned by the flag-format oracle
  6. confirm by feeding the recovered phrase back through the real enkivm

usage: solve.py [asherah.nam] [enkivm]
"""
import os
import struct
import subprocess
import sys

# --- ISA, recovered by reversing enkivm -----------------------------------
OPC = {0x00: 'HALT', 0x11: 'LOADI', 0x22: 'MOV', 0x33: 'ADD', 0x44: 'SUB',
       0x55: 'XOR', 0x66: 'AND', 0x77: 'MIX', 0x88: 'LOAD', 0x99: 'STORE',
       0xAA: 'CMP', 0xBB: 'JMP', 0xCC: 'JZ', 0xDD: 'JNZ', 0xEE: 'IN', 0xFF: 'OUT'}
TWO_REG = {'MOV', 'ADD', 'SUB', 'XOR', 'AND', 'LOAD', 'STORE', 'CMP'}
JUMPS = {'JMP', 'JZ', 'JNZ'}


def parse(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'NAM\x00', "not a nam-shub"
    code_len, data_len = struct.unpack('>HH', b[4:8])
    code = b[8:8 + code_len]
    data = b[8 + code_len:8 + code_len + data_len]
    return code, data


def disasm(code):
    return [(off, OPC.get(code[off], '??'), code[off + 1], code[off + 2], code[off + 3])
            for off in range(0, len(code), 4)]


def fmt(ins):
    off, name, a, b, imm = ins
    if name in JUMPS:  return f"{off:04x}: {name:5} ->{(a << 8 | b):04x}"
    if name == 'LOADI': return f"{off:04x}: {name:5} R{a}, 0x{imm:02x}"
    if name in TWO_REG: return f"{off:04x}: {name:5} R{a}, R{b}"
    if name in ('MIX', 'IN', 'OUT'): return f"{off:04x}: {name:5} R{a}"
    return f"{off:04x}: {name}"


def extract_constants(instrs):
    """Locate the transform triple ADD/XOR/MIX on one register, then read the
    constants that feed it off the setup LOADIs."""
    work = acc = roll = None
    for i in range(len(instrs) - 2):
        (n0, a0, b0), (n1, a1, b1), (n2, a2, _) = (instrs[i][1:4],
                                                   instrs[i + 1][1:4],
                                                   instrs[i + 2][1:4])
        if (n0, n1, n2) == ('ADD', 'XOR', 'MIX') and a0 == a1 == a2:
            work, acc, roll = a0, b0, b1
            break
    assert work is not None, "couldn't locate the transform"
    # K1 is added into the accumulator each iteration: ADD acc, k1reg
    k1reg = next(b for (_, n, a, b, _) in instrs if n == 'ADD' and a == acc and b != work)

    def first_loadi(reg):
        return next(imm for (_, n, a, _, imm) in instrs if n == 'LOADI' and a == reg)

    return work, acc, roll, first_loadi(k1reg), first_loadi(roll)


def recover(target, K1, K2, sbox_inv):
    phrase = bytearray()
    roll = K2
    for i, t in enumerate(target):
        u = sbox_inv[t]                       # u = ((in[i] + i*K1) ^ roll) & 0xFF
        phrase.append(((u ^ roll) - i * K1) & 0xFF)
        roll = t
    return bytes(phrase)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    nam = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'dist', 'asherah.nam')
    vm = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', 'dist', 'enkivm')

    code, data = parse(nam)
    instrs = disasm(code)
    print("=== disassembly of asherah.nam ===")
    for ins in instrs:
        print("  " + fmt(ins))

    work, acc, roll, K1, K2 = extract_constants(instrs)
    print(f"\n[+] transform: work=R{work}  acc(i*K1)=R{acc}  roll=R{roll}")
    print(f"[+] constants read from bytecode: K1=0x{K1:02x}  K2=0x{K2:02x}")

    sbox = list(data[:256])
    assert len(set(sbox)) == 256, "S-box not a bijection?!"
    sbox_inv = [0] * 256
    for x, y in enumerate(sbox):
        sbox_inv[y] = x

    dlen = len(data)
    found = None
    for N in range(16, dlen - 256):          # M = dlen-256-N >= 1
        target = data[256:256 + N]
        flag_ct = data[256 + N:dlen]
        phrase = recover(target, K1, K2, sbox_inv)
        flag = bytes(flag_ct[j] ^ phrase[j % N] for j in range(len(flag_ct)))
        if flag[:5] == b'flag{' and flag[-1:] == b'}' and all(32 <= c < 127 for c in flag):
            found = (N, phrase, flag)
            break
    assert found, "flag oracle found no consistent N"
    N, phrase, flag = found

    print(f"[+] split pinned by flag oracle: N={N}  (target@256, flag_ct@{256 + N})")
    print(f"[+] nam-shub  : {phrase.decode(errors='replace')!r}")
    print(f"[+] flag (inv): {flag.decode()}")

    # independent confirmation through the real VM
    r = subprocess.run([vm, nam], input=phrase, capture_output=True, timeout=10)
    via_vm = r.stdout
    print(f"[+] flag (VM) : {via_vm.decode(errors='replace')}")
    ok = via_vm.strip() == flag
    print(f"[{'+' if ok else '!'}] VM output matches inversion: {ok}")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
