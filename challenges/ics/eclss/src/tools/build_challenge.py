#!/usr/bin/env python3
"""
build_challenge.py  -  generate the RazorHack ECLSS challenge artifacts.

Reads flags.json and the ST templates in plc/src/, then writes:
  build/ECLSS.st                 complete IEC 61131-3 source
  build/program.zip              STruC++-compiled upload bundle (needs STruC++,
                                 see tools/bundle.py; use the builder container)
  build/modbus_slave.json        OpenPLC modbus_slave plugin config (conf/)
  build/maint_values.json        values the hidden Ignition /maint page shows
  docs/REGISTER_MAP.md           generated Modbus address reference

Flag text is packed into INT holding registers, 2 ASCII chars per register,
low byte first, and only copied into the published registers once the
matching objective bit is set in FlagsEarned. So a Modbus sweep of an
unsolved rig reads zeros for the gated flags.

Run from the repo root:  python3 tools/build_challenge.py
"""
import json
import datetime as _dt
# fresh per build so the gateway sees regenerated resources as modified
BUILD_STAMP = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "plc" / "src"
BUILD = ROOT / "build"
DOCS = ROOT / "docs"

# flag name -> (base %MW offset, objective bit, description)
# ghost_deck and disarm flags are delivered through Ignition, not Modbus.
FLAG_LAYOUT = {
    "banner": (100, None, "always readable - recon"),
    "o2":     (120, 0,    "O2 restored and in range"),
    "co2":    (140, 1,    "CO2 scrubbed into range"),
    "temp":   (160, 2,    "cabin temperature in range"),
    "disarm": (180, 3,    "MaintSync routine disarmed"),
    "final":  (200, 4,    "full nominal hold achieved"),
}
REG_PER_FLAG = 16  # 16 INT regs = 32 ASCII chars max


def pack(flag: str):
    b = flag.encode("ascii")
    if len(b) > REG_PER_FLAG * 2:
        raise SystemExit(f"flag too long ({len(b)} > {REG_PER_FLAG*2}): {flag}")
    regs = []
    for i in range(REG_PER_FLAG):
        lo = b[2 * i] if 2 * i < len(b) else 0
        hi = b[2 * i + 1] if 2 * i + 1 < len(b) else 0
        val = lo | (hi << 8)
        if val >= 32768:  # keep inside signed INT
            val -= 65536
        regs.append(val)
    return regs


def main():
    cfg = json.loads((ROOT / "flags.json").read_text())
    ship = cfg["ship_name"]
    code = int(cfg["disarm_code"])
    flags = cfg["flags"]
    if not (1 <= code <= 32767):
        raise SystemExit("disarm_code must be 1..32767")
    if code in (1001, 1002, 1003, 1004, 1005, 1111):
        raise SystemExit("disarm_code 1001-1005 and 1111 are used as wrong guesses by the unit tests - pick another")

    decls, publish = [], []
    for name, (base, bit, _desc) in FLAG_LAYOUT.items():
        if name not in flags:
            continue
        for i in range(REG_PER_FLAG):
            decls.append(f"    F_{name}_{i:02d} AT %MW{base + i} : INT;")
        regs = pack(flags[name])
        lines = []
        if bit is None:
            cond = None
        else:
            cond = f"(eclss.FlagsEarned AND {1 << bit}) <> 0"
        body = [f"        F_{name}_{i:02d} := {regs[i]};" for i in range(REG_PER_FLAG)]
        if cond is None:
            publish.append("    (* %s: %s *)" % (name, "always readable"))
            publish.extend(b[4:] for b in body)  # unindent one level
        else:
            publish.append(f"    IF {cond} THEN  (* flag: {name} *)")
            publish.extend(body)
            publish.append("    END_IF;")

    core = (SRC / "ECLSS_Core.st.tmpl").read_text()
    core = core.replace("{{SHIP_NAME}}", ship).replace("{{DISARM_KEY}}", str(code))

    main_src = (SRC / "ECLSS_Main.st.tmpl").read_text()
    main_src = (main_src
                .replace("{{SHIP_NAME}}", ship)
                .replace("{{FLAG_DECLS}}", "\n".join(decls))
                .replace("{{FLAG_PUBLISH}}", "\n".join(publish)))

    BUILD.mkdir(exist_ok=True)
    st_out = BUILD / "ECLSS.st"
    st_out.write_text(core + "\n\n" + main_src + "\n")

    # OpenPLC modbus_slave plugin config: bind TCP 502, segmented buffers
    modbus = {
        "network_configuration": {"host": "0.0.0.0", "port": 502},
        "word_order": "high_word_first",
        "buffer_mapping": {
            "holding_registers": {"qw_count": 1024, "mw_count": 1024,
                                  "md_count": 0, "ml_count": 0},
            "coils": {"qx_bits": 64, "mx_bits": 0},
            "discrete_inputs": {"ix_bits": 64},
            "input_registers": {"iw_count": 64},
        },
    }
    modbus_text = json.dumps(modbus, indent=2) + "\n"
    (BUILD / "modbus_slave.json").write_text(modbus_text)

    # program.zip = STruC++-generated C++ + runtime headers + defines.h +
    # conf/modbus_slave.json (auto-enables the Modbus TCP slave on 502).
    # The v4 runtime compiles C++ only; it rejects raw ST.
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools"))
    from bundle import make_bundle
    bundled = make_bundle(st_out, BUILD / "program.zip",
                          {"modbus_slave": BUILD / "modbus_slave.json"})
    if not bundled and (BUILD / "program.zip").exists():
        (BUILD / "program.zip").unlink()   # never leave a stale/invalid bundle

    (BUILD / "maint_values.json").write_text(json.dumps({
        "ship_name": ship,
        "disarm_code": code,
        "ghost_deck_flag": flags.get("ghost_deck", ""),
    }, indent=2) + "\n")

    write_register_map(ship, flags)
    write_ignition(ship, code, flags)
    print("Built:")
    for p in ["ECLSS.st", "program.zip", "modbus_slave.json", "maint_values.json"]:
        print("  build/" + p)
    print("  docs/REGISTER_MAP.md")
    print("  ignition/tags/ECLSS_tags.json")
    print("  ignition/projects/eclss/.../MaintConsole/view.json")
    print(f"\nDisarm code (keep secret): {code}")


IGN_PROJ = "ignition/projects/eclss/com.inductiveautomation.perspective/views"


def write_ignition(ship, code, flags):
    """Generate the Modbus-bound tag export and the templated hidden maint view.
    The HMI dashboard and the 'ghost' crew-manifest view are static files."""
    # ---- Tag export (Ignition JSON tag format) bound to the Modbus device ----
    dev = "ECLSS_PLC"
    srv = "Ignition OPC UA Server"

    def tag(name, prefix, addr, dtype="Int2"):
        # Modbus driver v2 OPC item: [Device]HR<addr> etc. Zero-based addressing
        # is enabled on the device so HR0 == Modbus holding register 0.
        return {
            "name": name, "tagType": "AtomicTag", "dataType": dtype,
            "valueSource": "opc", "opcServer": srv,
            # 8.3 Modbus item paths need the unit ID; +1 because Ignition devices
            # count registers from 1 by default ("One-based Addressing").
            "opcItemPath": f"ns=1;s=[{dev}]1.{prefix}{addr + 1}",
        }

    tele = [("O2_x100", 0), ("CO2_ppm", 1), ("Temp_x100", 2), ("Press_x10", 3),
            ("OGA_x10", 4), ("BedA_x10", 5), ("BedB_x10", 6), ("ActiveBed", 7),
            ("Valve_x10", 8), ("Heater_x10", 9), ("AlarmWord", 10),
            ("CrewStatus", 11), ("MET_s", 12), ("NominalHold_s", 13),
            ("FlagsEarned", 14), ("CrewCount", 15), ("StatusBits", 16)]
    sp = [("O2_SP_x100", 0), ("O2_Kp_x10", 1), ("CDRA_Mode", 2),
          ("CDRA_HalfCycle_s", 3), ("Temp_SP_x100", 4), ("TCS_Kp_x10", 5),
          ("Disarm_Code", 6)]
    coils = [("OGA_Inhibit", 0), ("CDRA_Heater_En", 1),
             ("TCS_Reverse", 2), ("Heater_Override", 3)]

    tags = {
        "name": "ECLSS", "tagType": "Folder", "tags": [
            {"name": "Telemetry", "tagType": "Folder",
             "tags": [tag(n, "HR", a) for n, a in tele]},
            {"name": "Setpoints", "tagType": "Folder",
             "tags": [tag(n, "HR", 1024 + a) for n, a in sp]},
            {"name": "Commands", "tagType": "Folder",
             "tags": [tag(n, "C", a, "Boolean") for n, a in coils]},
        ],
    }
    out = ROOT / "ignition" / "tags"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ECLSS_tags.json").write_text(json.dumps(tags, indent=2) + "\n")

    # ---- Perspective views (deep-space theme, tools/hmi_theme.py) ----
    from hmi_theme import eclss_overview, terminal_page, RED, VIOLET

    def put(name, view):
        d = ROOT / IGN_PROJ / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "view.json").write_text(json.dumps(view, indent=2, ensure_ascii=False) + "\n")
        _resource(d)

    put("ECLSSOverview", eclss_overview(ship))

    # hidden maintenance page (carries the disarm code). Flag 6 is NOT on the
    # page: the PLC publishes it only once the code is actually written.
    maint_md = (
        "**RESTRICTED - certified technicians only**\n\n"
        "MaintSync periodically re-applies the commissioning baseline while it is "
        "armed. To stand it down, write the code below to holding register "
        "**1030** (`Setpoints/Disarm_Code`).\n\n"
        f"- Maintenance disarm code: **{code}**\n"
        "- Once the PLC accepts the code it publishes a sign-off token with its "
        "other text blocks.\n\n"
        "_Five wrong codes lock the register for 60 s._"
    )
    put("MaintConsole", terminal_page(
        ship.upper() + "  ·  MAINTENANCE", "ECLSS SERVICE TERMINAL  ·  AUTHORIZED PERSONNEL",
        "RESTRICTED", RED, maint_md))

    # unlinked "ghost" page (carries flag 2)
    ghost_md = (
        "This console was retired at launch and removed from the operator "
        "menu, but the page was never deleted from the gateway.\n\n"
        "If you are reading this, you found an unlinked Perspective page.\n\n"
        f"Archive access token: `{flags.get('ghost_deck', '')}`"
    )
    put("CrewManifest", terminal_page(
        ship.upper() + "  ·  CREW MANIFEST", "ARCHIVED CONSOLE  ·  DECOMMISSIONED AT LAUNCH",
        "ARCHIVED", VIOLET, ghost_md))


def _resource(vdir):
    (vdir / "resource.json").write_text(json.dumps({
        "scope": "G", "version": 1,
        "restricted": False, "overridable": True,
        "files": ["view.json"],
        "attributes": {"lastModification": {"actor": "razorhack",
                                            "timestamp": BUILD_STAMP}},
    }, indent=2) + "\n")


def write_register_map(ship, flags):
    DOCS.mkdir(exist_ok=True)
    tele = [
        (0, "O2_x100", "cabin O2 %, x100"),
        (1, "CO2_ppm", "cabin CO2, ppm"),
        (2, "Temp_x100", "cabin temp degC, x100"),
        (3, "Press_x10", "cabin pressure kPa, x10"),
        (4, "OGA_x10", "O2 generator output %, x10"),
        (5, "BedA_x10", "CDRA bed A saturation %, x10"),
        (6, "BedB_x10", "CDRA bed B saturation %, x10"),
        (7, "ActiveBed", "1=A adsorbing, 2=B adsorbing"),
        (8, "Valve_x10", "coolant valve %, x10"),
        (9, "Heater_x10", "trim heater %, x10"),
        (10, "AlarmWord", "bit0 O2lo bit1 O2hi bit2 CO2hi bit3 cold bit4 hot bit5 tamper"),
        (11, "CrewStatus", "0 OK / 1 WARN / 2 CRIT"),
        (12, "MET_s", "mission elapsed time, s"),
        (13, "NominalHold_s", "consecutive s all-nominal"),
        (14, "FlagsEarned", "objective bitfield"),
        (15, "CrewCount", "souls aboard"),
        (16, "StatusBits", "bit0 MaintSyncArmed, bit1 TamperLockout"),
    ]
    sp = [
        (1024, "O2_SP_x100", "O2 setpoint %, x100 (nominal 2095)"),
        (1025, "O2_Kp_x10", "OGA gain, x10"),
        (1026, "CDRA_Mode", "0 OFF / 1 AUTO / 2 MAN_A / 3 MAN_B"),
        (1027, "CDRA_HalfCycle_s", "bed swing half-cycle, s"),
        (1028, "Temp_SP_x100", "temp setpoint degC, x100 (nominal 2250)"),
        (1029, "TCS_Kp_x10", "TCS gain, x10"),
        (1030, "Disarm_Code", "write the maintenance code here to stop MaintSync"),
    ]
    lines = [
        f"# Modbus Register Map - {ship}", "",
        "Modbus TCP, unit id 1, port 502. All values are 16-bit signed INT.",
        "Scaled values are stored x10 or x100 (divide to read).", "",
        "## Telemetry - Holding Registers (function code 3), read",
        "", "| HR | Name | Meaning |", "|----|------|---------|",
    ]
    lines += [f"| {a} | {n} | {d} |" for a, n, d in tele]
    lines += ["", "## Setpoints / Commands - Holding Registers (FC 3 read / FC 6,16 write)",
              "", "| HR | Name | Meaning |", "|----|------|---------|"]
    lines += [f"| {a} | {n} | {d} |" for a, n, d in sp]
    lines += ["", "## Commands - Coils (FC 1 read / FC 5 write)",
              "", "| Coil | Name | Meaning |", "|------|------|---------|",
              "| 0 | OGA_Inhibit | stop oxygen generation |",
              "| 1 | CDRA_Heater_En | enable CDRA regen heater |",
              "| 2 | TCS_Reverse | reverse coolant valve action (mis-wire) |",
              "| 3 | Heater_Override | force trim heater to 100% |"]
    lines += ["", "## Published flag text - Holding Registers", "",
              "ASCII packed 2 chars per register, low byte first. A block reads",
              "zero until its objective bit is set in FlagsEarned (HR 14).", "",
              "| HR range | Flag | Gate |", "|----------|------|------|"]
    gate = {"banner": "none (recon)", "o2": "FlagsEarned bit0",
            "co2": "bit1", "temp": "bit2", "disarm": "bit3", "final": "bit4"}
    for name, (base, _bit, _d) in FLAG_LAYOUT.items():
        if name in flags:
            lines.append(f"| {1024+base}..{1024+base+15} | {name} | {gate.get(name)} |")
    (DOCS / "REGISTER_MAP.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
