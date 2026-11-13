#!/usr/bin/env python3
# 4x4 Sudoku Solution
A = [3, 1, 4, 2, 4, 2, 1, 2, 3, 4, 3, 1, 2, 4, 1, 3]
A = [a - 1 for a in A]

L = 0
for a in A:
    L = (L << 2) | a

print(hex(L))

A = 0x19c60d
B = 0x3c6ef35f
for _ in range(255):
    L = (L * A) & 0xffffffff
    L = (L + B) & 0xffffffff
    print(hex(L))

from itertools import cycle
L = [
    (L >> 0x00) & 0xff,
    (L >> 0x08) & 0xff,
    (L >> 0x10) & 0xff,
    (L >> 0x18) & 0xff,
]

print(f'[{', '.join(f'0x{l:02x}' for l in L)}]')
L = cycle(L)
flag = 'flag{c++_is_an_interpreted_langauge}'

print(f'[{', '.join(f'0x{l^ord(f):02x}' for l, f in zip(L, flag))}]')
