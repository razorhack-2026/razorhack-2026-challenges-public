def xorshift(x: int):
    x ^= x << 13;
    x &= 0xFFFFFFFFFFFFFFFF

    x ^= x >> 7;
    x &= 0xFFFFFFFFFFFFFFFF

    x ^= x << 15;
    x &= 0xFFFFFFFFFFFFFFFF

    return x

def xorhash(initial_state: int):
    state = (initial_state & 0xFFFF) + 0xBEEF
    for _ in range(16):
        state = xorshift(state)

    return state

mem = {}
for n in range(2**16):
    H = xorhash(n)
    assert H not in mem
    mem[H] = n

flag = list(b'\x15\x0f\x08\x02\x15\x19\x10\x2c\x1c\x1c\x32\x17\x08\x17\x01\x04\x33\x37\x15\x1b\x0d\x00\x15\x19\x19\x1a')

checks = [0xe4b32e6150bb6fde, 0x6d0a99d34868bac6, 0x8fbecef0ef654aec, 0x6fe2381f446a074b, 0x5f2a203f1cab029d, 0x9cac2cfa67ca4b47, 0xce13f87c924db6f0, 0xf52d7f264fadaa96, 0x3ff0a518df37dd6e, 0x6414a765c14b1efb, 0x28ac48849cc4e36e, 0xda1dc182a6cc8cad, 0x868bb4a5ac971077]

inpt = []
for i, check in enumerate(checks):
    n = mem[check]
    inpt += [(n >> 0) & 0xFF, (n >> 8) & 0xFF]
    flag[2*i  ] ^= (n >> 0) & 0xFF
    flag[2*i+1] ^= (n >> 8) & 0xFF

print(f'input: {''.join(chr(c) for c in inpt)}')
print(f'flag:  {''.join(chr(c) for c in flag)}')
