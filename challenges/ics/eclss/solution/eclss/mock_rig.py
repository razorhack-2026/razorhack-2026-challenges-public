#!/usr/bin/env python3
"""
mock_rig.py - INDEPENDENT validation harness for solve.py and the register map.

It is NOT the challenge runtime (the real rig is OpenPLC running build/ECLSS.st).
It is a minimal raw-socket Modbus TCP server (FC 1/3/5/6/16) wrapped around a
coarse reimplementation of the ECLSS register contract: MaintSync arms and
forces the bad setpoints, the disarm code stands it down, good setpoints clear
the alarms, a nominal hold sets the objective bits, and the flag blocks unlock.
Flag text comes from flags.json via the same packer as the builder. Time is
accelerated so the nominal hold completes in a few seconds.

Run:  python3 solution/eclss/mock_rig.py   (listens on 127.0.0.1:1502)
"""
import json
import pathlib
import socket
import struct
import sys
import threading
import time

# razorhack-2026 layout: this file is solution/eclss/, the kit (tools/, flags.json) is src/
ROOT = pathlib.Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(ROOT / "tools"))
from build_challenge import pack, FLAG_LAYOUT

cfg = json.loads((ROOT / "flags.json").read_text())
DISARM = int(cfg["disarm_code"])
FLAGS = cfg["flags"]

HR = [0] * 1300       # holding registers (signed stored as 0..65535)
CO = [0] * 32         # coils
lock = threading.Lock()


def sim():
    o2, co2, temp = 20.9, 2600.0, 22.5
    armed, sync, wrong, lockt, last, hold = True, 2.0, 0, 0.0, 0, 0.0
    with lock:
        HR[1024], HR[1026], HR[1028] = 2095, 1, 2250
    while True:
        dt = 0.1
        with lock:
            code = HR[1030]
            heater_en = CO[1]
        if lockt > 0:
            lockt = max(0.0, lockt - dt)
        if code != last and code != 0:
            last = code
            if lockt <= 0:
                if code == DISARM:
                    armed = False
                else:
                    wrong += 1
                    sync = 2.0
                    if wrong >= 5:
                        lockt, wrong = 60.0, 0
            with lock:
                HR[1030] = 0
        if armed:
            sync += dt
            if sync >= 2.0:
                sync = 0.0
                with lock:
                    HR[1024], HR[1026], HR[1028] = 1850, 2, 3100

        with lock:
            o2sp, mode, tsp = HR[1024] / 100.0, HR[1026], HR[1028] / 100.0

        o2 += (2.0 * (o2sp - o2)) * 0.5 * dt + 0.44 * dt
        if mode == 1:
            co2 += 55.0 * dt - (95.0 if heater_en else 80.0) * dt
        else:
            co2 += 55.0 * dt - 10.0 * dt
        co2 = max(350.0, co2)
        temp += (0.30 - 0.015 * (40 + 3 * (temp - tsp) * 10)) * dt

        alarm = 0
        if o2 < 19.5: alarm |= 1
        if o2 > 23.5: alarm |= 2
        if co2 > 5000: alarm |= 4
        if temp < 18.0: alarm |= 8
        if temp > 27.0: alarm |= 16
        if armed: alarm |= 32
        hold = hold + dt if alarm == 0 else 0.0

        fl = 0
        if 19.5 <= o2 <= 23.5: fl |= 1
        if co2 <= 5000: fl |= 2
        if 18.0 <= temp <= 27.0: fl |= 4
        if not armed: fl |= 8
        if hold >= 30.0 and not armed: fl |= 16

        with lock:
            HR[0], HR[1], HR[2] = int(o2 * 100), int(co2), int(temp * 100)
            HR[10], HR[13], HR[14], HR[15] = alarm, int(hold), fl, 4
            HR[16] = (1 if armed else 0) | (2 if lockt > 0 else 0)
            for name, (base, bit, _d) in FLAG_LAYOUT.items():
                if name not in FLAGS:
                    continue
                on = bit is None or (fl & (1 << bit))
                regs = pack(FLAGS[name]) if on else [0] * 16
                for i, v in enumerate(regs):
                    HR[1024 + base + i] = v & 0xFFFF
        time.sleep(0.01)


def handle(conn):
    while True:
        head = recvn(conn, 7)
        if not head:
            return
        tid, pid, length, uid = struct.unpack(">HHHB", head)
        body = recvn(conn, length - 1)
        if not body:
            return
        fc = body[0]
        resp = b""
        with lock:
            if fc in (3, 4):  # read holding / input registers
                addr, cnt = struct.unpack(">HH", body[1:5])
                vals = HR[addr:addr + cnt]
                resp = bytes([fc, cnt * 2]) + b"".join(struct.pack(">H", v & 0xFFFF) for v in vals)
            elif fc == 1:     # read coils
                addr, cnt = struct.unpack(">HH", body[1:5])
                bits = CO[addr:addr + cnt]
                nbytes = (cnt + 7) // 8
                buf = bytearray(nbytes)
                for i, b in enumerate(bits):
                    if b:
                        buf[i // 8] |= 1 << (i % 8)
                resp = bytes([fc, nbytes]) + bytes(buf)
            elif fc == 6:     # write single register
                addr, val = struct.unpack(">HH", body[1:5])
                HR[addr] = val
                resp = body[:5]
            elif fc == 16:    # write multiple registers
                addr, cnt, _bc = struct.unpack(">HHB", body[1:6])
                for i in range(cnt):
                    HR[addr + i] = struct.unpack(">H", body[6 + i * 2:8 + i * 2])[0]
                resp = bytes([fc]) + struct.pack(">HH", addr, cnt)
            elif fc == 5:     # write single coil
                addr, val = struct.unpack(">HH", body[1:5])
                CO[addr] = 1 if val == 0xFF00 else 0
                resp = body[:5]
            else:
                resp = bytes([fc | 0x80, 0x01])
        conn.sendall(struct.pack(">HHHB", tid, pid, len(resp) + 1, uid) + resp)


def recvn(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def run(port=1502):
    threading.Thread(target=sim, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(5)
    print(f"mock rig on 127.0.0.1:{port} (disarm code {DISARM})", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    run()
