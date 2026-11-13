#!/usr/bin/env python3
"""
Minimal pure-stdlib Modbus/TCP client. Pushed onto the CoreWatch web container
during the solve because the PLC on 127.0.0.1:502 is reachable only from inside
the shared task namespace (no host port), and the web container has bare
python3 (no pymodbus).

Writes the given words to holding registers 0.., then reads coil 0 (GATE_OPEN)
and holding registers 10..21 (flag readback), and prints them as JSON.

usage: mb_drive.py <host> <port> [word0 word1 ...]   words accept 0x / decimal
"""
import json
import socket
import struct
import sys
import time


def _recvn(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c:
            raise IOError("connection closed")
        b += c
    return b


def _txn(s, tid, pdu):
    frame = struct.pack(">HHHB", tid, 0, len(pdu) + 1, 1) + pdu
    s.sendall(frame)
    tid_r, proto, length, unit = struct.unpack(">HHHB", _recvn(s, 7))
    return _recvn(s, length - 1)  # PDU: func, ...


def main():
    host, port = sys.argv[1], int(sys.argv[2])
    words = [int(x, 0) & 0xFFFF for x in sys.argv[3:]]
    s = socket.create_connection((host, port), timeout=8)
    try:
        if words:
            qty = len(words)
            pdu = struct.pack(">BHHB", 0x10, 0, qty, qty * 2)
            pdu += b"".join(struct.pack(">H", w) for w in words)
            _txn(s, 1, pdu)
            time.sleep(0.25)
        # read coil 0 (GATE_OPEN)
        d = _txn(s, 2, struct.pack(">BHH", 0x01, 0, 1))
        # d[0]=func, d[1]=bytecount, d[2]=bits
        gate = d[2] & 1 if len(d) >= 3 else 0
        # read holding registers 10..21 (flag readback)
        d = _txn(s, 3, struct.pack(">BHH", 0x03, 10, 12))
        bc = d[1]
        regs = struct.unpack(">" + "H" * (bc // 2), d[2:2 + bc])
        bb = bytearray()
        for r in regs:
            bb += bytes([(r >> 8) & 0xFF, r & 0xFF])
        flag = bb.split(b"\x00")[0].decode("utf-8", "replace")
        print(json.dumps({"gate": int(gate), "flag": flag}))
    finally:
        s.close()


if __name__ == "__main__":
    main()
