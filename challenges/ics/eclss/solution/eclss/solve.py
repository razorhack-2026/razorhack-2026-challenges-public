#!/usr/bin/env python3
"""
solve.py - reference solution / health check for the RazorHack ECLSS challenge.

Organizers: run this against a freshly provisioned rig to confirm every flag
is reachable before the event. Players: this is the intended Modbus path (the
ghost-page and maintenance flags also live on the Ignition HMI).

It:
  1. reads the always-on banner flag,
  2. shows that MaintSync is armed and the setpoints are mis-configured,
  3. writes the maintenance disarm code (default 7982) to HR1030,
  4. writes correct setpoints and enables the CDRA regen heater,
  5. holds until the cabin is nominal and harvests each gated flag.

Usage:
  pip install -r requirements.txt
  python3 solve.py --host 127.0.0.1 --port 502 --code 7982
"""
import argparse
import sys
import time

import inspect

from pymodbus.client import ModbusTcpClient

# pymodbus renamed the unit kwarg over 3.x: unit= -> slave= -> device_id=.
# Pick whichever this install accepts so the solver works across versions.
_UNIT_KW = "device_id"
for _kw in ("device_id", "slave", "unit"):
    if _kw in inspect.signature(ModbusTcpClient.read_holding_registers).parameters:
        _UNIT_KW = _kw
        break


def _unit():
    return {_UNIT_KW: 1}


# Register map (see docs/REGISTER_MAP.md)
HR_O2, HR_CO2, HR_TEMP = 0, 1, 2
HR_ALARM, HR_MET, HR_HOLD, HR_FLAGS, HR_CREW, HR_STATUS = 10, 12, 13, 14, 15, 16
HR_O2_SP, HR_CDRA_MODE, HR_TEMP_SP, HR_DISARM = 1024, 1026, 1028, 1030
C_CDRA_HEATER = 1

FLAG_REGS = {
    "banner": 1124, "o2": 1144, "co2": 1164,
    "temp": 1184, "disarm": 1204, "final": 1224,
}
FLAG_BIT = {"o2": 0, "co2": 1, "temp": 2, "disarm": 3, "final": 4}


def rd(client, addr, count=1):
    r = client.read_holding_registers(addr, count=count, **_unit())
    if r.isError():
        raise SystemExit(f"Modbus read error at HR{addr}: {r}")
    return r.registers


def wr(client, addr, value):
    r = client.write_register(addr, value & 0xFFFF, **_unit())
    if r.isError():
        raise SystemExit(f"Modbus write error at HR{addr}: {r}")


def decode_flag(client, addr):
    regs = rd(client, addr, 16)
    b = bytearray()
    for v in regs:
        b.append(v & 0xFF)
        b.append((v >> 8) & 0xFF)
    text = b.split(b"\x00")[0].decode("ascii", "replace")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--code", type=int, default=7982, help="maintenance disarm code")
    ap.add_argument("--timeout", type=int, default=300, help="seconds to wait for nominal (a long-sabotaged ship needs ~4 min)")
    args = ap.parse_args()

    c = ModbusTcpClient(args.host, port=args.port, timeout=5)
    if not c.connect():
        raise SystemExit(f"cannot connect to {args.host}:{args.port}")
    found = {}

    print(f"[*] banner flag: {decode_flag(c, FLAG_REGS['banner'])}")
    found["banner"] = decode_flag(c, FLAG_REGS["banner"])

    status = rd(c, HR_STATUS)[0]
    print(f"[*] StatusBits=0x{status:04x} "
          f"(MaintSyncArmed={bool(status & 1)}, TamperLockout={bool(status & 2)})")
    print(f"[*] forced setpoints: O2_SP={rd(c,HR_O2_SP)[0]} "
          f"CDRA_Mode={rd(c,HR_CDRA_MODE)[0]} Temp_SP={rd(c,HR_TEMP_SP)[0]}")

    print(f"[*] writing disarm code {args.code} to HR{HR_DISARM}")
    wr(c, HR_DISARM, args.code)
    time.sleep(0.5)

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        # keep correcting the setpoints (harmless once disarmed)
        wr(c, HR_O2_SP, 2095)
        wr(c, HR_CDRA_MODE, 1)
        wr(c, HR_TEMP_SP, 2250)
        c.write_coil(C_CDRA_HEATER, True, **_unit())

        o2 = rd(c, HR_O2)[0] / 100.0
        co2 = rd(c, HR_CO2)[0]
        temp = rd(c, HR_TEMP)[0] / 100.0
        alarm = rd(c, HR_ALARM)[0]
        hold = rd(c, HR_HOLD)[0]
        flags = rd(c, HR_FLAGS)[0]

        for name, bit in FLAG_BIT.items():
            if name not in found and (flags & (1 << bit)):
                val = decode_flag(c, FLAG_REGS[name])
                if val and val.startswith("flag{"):
                    found[name] = val
                    print(f"[+] flag '{name}': {val}")

        sys.stdout.write(
            f"\r    O2={o2:5.2f}%  CO2={co2:5d}ppm  T={temp:5.1f}C  "
            f"alarm=0x{alarm:02x}  hold={hold:3d}s  flags=0x{flags:02x}   ")
        sys.stdout.flush()

        if len(found) == len(FLAG_REGS):
            break
        time.sleep(1.0)

    print("\n")
    c.close()

    print("==== flags recovered over Modbus ====")
    for name in ("banner", "o2", "co2", "temp", "disarm", "final"):
        print(f"  {name:8}: {found.get(name, '(not captured)')}")
    missing = [k for k in FLAG_REGS if k not in found]
    if missing:
        print(f"\n[!] not captured: {missing} "
              f"(hold longer with --timeout, or check the rig)")
        sys.exit(1)
    print("\n[*] all Modbus flags captured - rig is healthy")
    print("[*] remember: ghost-page and maint flags also live on the Ignition HMI")


if __name__ == "__main__":
    main()
