#!/usr/bin/env python3
"""
build_training.py - generate the RazorHack Training Bay (basic Modbus /
OpenPLC / Ignition warm-up challenges) from training/training_flags.json.

Writes:
  build/training/TRAINING.st            full IEC 61131-3 program
  build/training/program.zip            STruC++ upload bundle (needs STruC++)
  build/training/modbus_slave.json      Modbus plugin config (also in the zip)
  build/training/flags_all.json         every flag incl. derived ones (staff)
  training/student/TRAINING_LOGIC.st    FB source for players, secrets redacted
  training/student/REGISTER_MAP.md      address map for players
  ignition/projects/training/...        Training HMI (IG2/IG3)
  ignition/tags/Training_tags.json      tag export (tools/ignition_config.py turns
                                        it into the gateway's config resources)

The training PLC listens on Modbus port 5020 itself: on Fargate it shares one
network namespace with the ECLSS PLC (502), so it can't be remapped.

Usage:  python3 training/tools/build_training.py
"""
import argparse
import json
import datetime as _dt
# fresh per build so the gateway sees regenerated resources as modified
BUILD_STAMP = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TR = ROOT / "training"
BUILD = ROOT / "build" / "training"
sys.path.insert(0, str(ROOT / "tools"))
from build_challenge import pack, REG_PER_FLAG   # same 2-chars/register packer
from bundle import make_bundle

# flag -> (base %QW address == holding register, unlock bit or None)
FLAG_LAYOUT = {
    "mb2": (10, None),
    "mb3": (200, None),
    "mb4": (300, 0),
    "pl1": (600, 1),
    "pl2": (620, 2),
    "pl3": (640, 3),
    "pl4": (660, 4),
    "pl5": (680, 5),
    "mb7": (700, 6),
}
TRAIN_MODBUS_PORT = 5020   # not 502: shares a network namespace with the ECLSS PLC


def s16(v):
    v &= 0xFFFF
    return v - 65536 if v >= 32768 else v


def load_cfg():
    cfg = json.loads((TR / "training_flags.json").read_text())
    for k in ("bay_id", "breaker_init", "beacon_freq"):
        if not 1 <= int(cfg[k]) <= 32767:
            raise SystemExit(f"{k} must be 1..32767")
    if not 65536 <= int(cfg["mb5_value"]) <= 2147483647:
        raise SystemExit("mb5_value must be 65536..2147483647 (so it spans two registers)")
    bit = int(cfg["breaker_bit"])
    if not 0 <= bit <= 14:
        raise SystemExit("breaker_bit must be 0..14")
    if int(cfg["breaker_init"]) & (1 << bit):
        raise SystemExit("breaker_init must have breaker_bit CLEAR")
    for name, text in cfg["flags"].items():
        if len(text.encode("ascii")) > REG_PER_FLAG * 2:
            raise SystemExit(f"flag {name} longer than {REG_PER_FLAG*2} chars")
    return cfg


def derived(cfg):
    v = int(cfg["mb5_value"])
    f32 = struct.unpack(">f", struct.pack(">f", float(cfg["mb6_value"])))[0]
    hi, lo = struct.unpack(">HH", struct.pack(">f", f32))
    flags = dict(cfg["flags"])
    flags["mb1"] = f"flag{{{int(cfg['bay_id'])}}}"
    flags["mb5"] = f"flag{{{v}}}"
    flags["mb6"] = f"flag{{{f32:.3f}}}"
    flags["ig1"] = f"flag{{{cfg['gateway_name']}}}"
    return {
        "BIG_HI": s16(v >> 16), "BIG_LO": s16(v),
        "FLT_HI": s16(hi), "FLT_LO": s16(lo),
        "BREAKER_GOAL": int(cfg["breaker_init"]) | (1 << int(cfg["breaker_bit"])),
    }, flags


def flag_code(cfg):
    decls, publish = [], []
    for name, (base, bit) in FLAG_LAYOUT.items():
        regs = pack(cfg["flags"][name])
        for i in range(REG_PER_FLAG):
            decls.append(f"    F_{name}_{i:02d} AT %QW{base + i} : INT;")
        if bit is None:
            publish.append(f"(* {name}: always readable *)")
            publish += [f"F_{name}_{i:02d} := {regs[i]};" for i in range(REG_PER_FLAG)]
        else:
            publish.append(f"IF (unlock AND {1 << bit}) <> 0 THEN   (* {name} *)")
            publish += [f"    F_{name}_{i:02d} := {regs[i]};" for i in range(REG_PER_FLAG)]
            publish.append("ELSE")
            publish += [f"    F_{name}_{i:02d} := 0;" for i in range(REG_PER_FLAG)]
            publish.append("END_IF;")
    return "\n".join(decls), "\n".join(publish)


def subst(text, mapping):
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def write_student(cfg):
    out = TR / "student"
    out.mkdir(parents=True, exist_ok=True)
    src = (TR / "plc" / "TRAIN_FBs.st.tmpl").read_text()
    src = subst(src, {
        "SHIP_NAME": "ISV Ozark Horizon",
        "BREAKER_BIT": cfg["breaker_bit"],
        "BREAKER_INIT": "16#????  (* REDACTED - read the live panel *)",
        "BREAKER_GOAL": "16#????  (* REDACTED *)",
        "BEACON_FREQ": "????  (* REDACTED - see the HMI *)",
    })
    hdr = ("(* Student copy of the Training Bay PLC logic. Secret constants are\n"
           "   redacted. Use it to work out WHAT the PLC wants; the register map\n"
           "   tells you WHERE to write it. *)\n\n")
    (out / "TRAINING_LOGIC.st").write_text(hdr + src)

    coils = [(0, "Beacon_On", "MB4 beacon command"),
             (8, "Inner_Closed", "PL1 inner door closed"),
             (9, "Suit_Ok", "PL1 suit check passed"),
             (10, "Override", "PL1 maintenance override"),
             (11, "Cycle_Req", "PL1 request outer door"),
             (16, "Hold_Btn", "PL2 confirm button"),
             (17, "Pulse_In", "PL3 pulse input"),
             (18, "Count_Reset", "PL3 counter reset"),
             (24, "Start_PB", "PL4 START (normally open)"),
             (25, "Stop_PB_NC", "PL4 STOP (normally CLOSED)"),
             (30, "Breaker_Reset", "MB7 panel reset")]
    w = [(1024, "Analog_Raw", "PL5 raw 4-20 mA ADC value"),
         (1025, "Breaker_Word", "MB7 breaker bitfield"),
         (1026, "Beacon_Freq", "IG3 beacon frequency (set it from the HMI)")]
    ro = [(0, "Bay_Id", "MB1"), (1, "Heartbeat", "increments every scan (100 ms)"),
          ("10..25", "text block", "MB2"), ("200..215", "text block", "MB3 (see briefing)"),
          ("300..315", "text block", "MB4, while the beacon is lit"),
          ("400..401", "32-bit value", "MB5"), ("410..411", "32-bit value", "MB6"),
          ("600..615", "text block", "PL1"), ("620..635", "text block", "PL2"),
          ("640..655", "text block", "PL3"), ("660..675", "text block", "PL4"),
          ("680..695", "text block", "PL5"), ("700..715", "text block", "MB7"),
          (730, "Diag_Count", "PL3 counter value"),
          (731, "Diag_Hold", "PL2 time held, 0.1 s"),
          (732, "Diag_Motor", "PL4 motor running (1/0)"),
          (733, "Diag_Eng", "PL5 scaled level, % x10 (-1 = wire break)"),
          (734, "Diag_Door", "PL1 outer door open (1/0)"),
          (735, "Diag_Trip", "MB7 panel tripped (1/0)"),
          (736, "Diag_Chamber", "PL1 chamber pressure kPa x10"),
          (737, "Diag_Fault", "PL3 overcount fault (1/0)"),
          (740, "IG3_Locked", "IG3 beacon locked (1/0)"),
          (745, "Unlock_Word", "bitfield of currently unlocked challenges")]
    L = ["# Training Bay - Register Map", "",
         "Modbus TCP, unit id 1. Holding registers are 0-based, 16-bit signed.",
         "Text blocks: ASCII, 2 chars per register, low byte first.", "",
         "## Coils (FC1 read / FC5 write)", "", "| Coil | Name | Purpose |", "|---|---|---|"]
    L += [f"| {a} | {n} | {d} |" for a, n, d in coils]
    L += ["", "## Player-writable holding registers (FC3 / FC6, FC16)", "",
          "| HR | Name | Purpose |", "|---|---|---|"]
    L += [f"| {a} | {n} | {d} |" for a, n, d in w]
    L += ["", "## Read-only holding registers (FC3)", "", "| HR | What | Notes |", "|---|---|---|"]
    L += [f"| {a} | {n} | {d} |" for a, n, d in ro]
    L += ["", "Gated text blocks read as zeros until you complete that challenge, "
          "and go back to zeros when the 20 s success window ends."]
    (out / "REGISTER_MAP.md").write_text("\n".join(L) + "\n")


def write_ignition(cfg, flags):
    dev, srv = "TRAIN_PLC", "Ignition OPC UA Server"

    def tag(name, prefix, addr):
        return {"name": name, "tagType": "AtomicTag", "dataType": "Int2",
                "valueSource": "opc", "opcServer": srv,
                # unit ID required in 8.3; +1 for the default one-based addressing
                "opcItemPath": f"ns=1;s=[{dev}]1.{prefix}{addr + 1}"}

    tags = {"name": "Training", "tagType": "Folder", "tags": [
        tag("Beacon_Freq", "HR", 1026), tag("IG3_Locked", "HR", 740),
        tag("Heartbeat", "HR", 1)]}
    tdir = ROOT / "ignition" / "tags"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "Training_tags.json").write_text(json.dumps(tags, indent=2) + "\n")

    res = {"scope": "G", "version": 1, "restricted": False, "overridable": True,
           "attributes": {"lastModification": {"actor": "razorhack",
                                               "timestamp": BUILD_STAMP}}}

    proj = ROOT / "ignition" / "projects" / "training"
    persp = proj / "com.inductiveautomation.perspective"
    vdir = persp / "views" / "TrainingHMI"
    vdir.mkdir(parents=True, exist_ok=True)
    (proj / "project.json").write_text(json.dumps({
        "title": "Training", "description": "RazorHack Training Bay HMI",
        "parent": "", "enabled": True, "inheritable": False}, indent=2) + "\n")
    # Perspective reads page config from page-config/config.json (+ resource.json)
    pcd = persp / "page-config"
    pcd.mkdir(parents=True, exist_ok=True)
    stale = persp / "page-config.json"
    if stale.exists():
        stale.unlink()
    (pcd / "config.json").write_text(json.dumps({
        "pages": {"/": {"title": "Training Bay", "viewPath": "TrainingHMI"}},
        "sharedDocks": {"cornerPriority": "top-bottom"}}, indent=2) + "\n")
    (pcd / "resource.json").write_text(json.dumps({**res, "files": ["config.json"]}, indent=2) + "\n")

    from hmi_theme import training_console
    view = training_console(cfg["beacon_clue"], flags["ig2"], flags["ig3"].replace("'", ""))
    (vdir / "view.json").write_text(json.dumps(view, indent=2, ensure_ascii=False) + "\n")
    (vdir / "resource.json").write_text(json.dumps({**res, "files": ["view.json"]}, indent=2) + "\n")


def main():
    argparse.ArgumentParser(description="Generate the Training Bay artifacts.").parse_args()

    cfg = load_cfg()
    d, flags = derived(cfg)
    decls, publish = flag_code(cfg)
    m = {"SHIP_NAME": "ISV Ozark Horizon", "BREAKER_BIT": cfg["breaker_bit"],
         "BREAKER_INIT": cfg["breaker_init"], "BEACON_FREQ": cfg["beacon_freq"],
         "BAY_ID": cfg["bay_id"], "FLAG_DECLS": decls, "FLAG_PUBLISH": publish, **d}
    fbs = subst((TR / "plc" / "TRAIN_FBs.st.tmpl").read_text(), m)
    main_src = subst((TR / "plc" / "TRAIN_Main.st.tmpl").read_text(), m)

    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "TRAIN_FBs.st").write_text(fbs)            # FBs only, for unit tests
    tests = subst((TR / "test" / "test_training.st").read_text(),
                  {**m, "BREAKER_MASK": 1 << int(cfg["breaker_bit"])})
    (BUILD / "test_training.st").write_text(tests)       # rendered with this event's secrets
    st = BUILD / "TRAINING.st"
    st.write_text(fbs + "\n\n" + main_src + "\n")
    modbus = {"network_configuration": {"host": "0.0.0.0", "port": TRAIN_MODBUS_PORT},
              "word_order": "high_word_first",
              "buffer_mapping": {
                  "holding_registers": {"qw_count": 1024, "mw_count": 1024, "md_count": 0, "ml_count": 0},
                  "coils": {"qx_bits": 64, "mx_bits": 0},
                  "discrete_inputs": {"ix_bits": 64},
                  "input_registers": {"iw_count": 64}}}
    (BUILD / "modbus_slave.json").write_text(json.dumps(modbus, indent=2) + "\n")
    ok = make_bundle(st, BUILD / "program.zip", {"modbus_slave": BUILD / "modbus_slave.json"})
    if not ok and (BUILD / "program.zip").exists():
        (BUILD / "program.zip").unlink()

    order = ["mb1", "mb2", "mb3", "mb4", "mb5", "mb6", "mb7",
             "pl1", "pl2", "pl3", "pl4", "pl5", "ig1", "ig2", "ig3"]
    (BUILD / "flags_all.json").write_text(json.dumps({k: flags[k] for k in order}, indent=2) + "\n")
    write_student(cfg)
    write_ignition(cfg, flags)

    print("Training Bay built:")
    print("  build/training/TRAINING.st" + ("" if ok else "   (program.zip SKIPPED - no STruC++)"))
    if ok:
        print("  build/training/program.zip")
    print("  build/training/flags_all.json   (staff only)")
    print("  training/student/TRAINING_LOGIC.st, REGISTER_MAP.md")
    print("  ignition/projects/training, ignition/tags/Training_tags.json")


if __name__ == "__main__":
    main()
