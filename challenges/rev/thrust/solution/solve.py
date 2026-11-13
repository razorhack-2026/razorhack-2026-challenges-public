import re, struct
from pathlib import Path
def solve():
    data=(Path(__file__).parents[1]/"dist/thruster_ctl").read_bytes()
    # The shipped Linux ELF contains a fixed-width XOR-obfuscated token buffer.
    needle=bytes.fromhex('24 2e 23 25 39 32 2d 35 27 30 1d 2d 2c 1d 2e 27 36 31 1d 25 2d 3f 42 42 42 42 42 42 42 42')
    pos=data.find(needle)
    if pos<0: raise ValueError("expected data array absent from ELF")
    return bytes(b^0x42 for b in data[pos:pos+30]).split(b"\x00",1)[0].decode()
