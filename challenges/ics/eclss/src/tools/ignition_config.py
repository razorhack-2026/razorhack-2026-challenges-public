#!/usr/bin/env python3
"""
ignition_config.py - write the Ignition 8.3 gateway config resources the
gateway image ships with, so a fresh gateway boots with both Modbus devices
and every tag already in place (no Designer, no Script Console).

Ignition 8.3 keeps its config as files under data/config/resources/<collection>/.
This writes that tree to ignition/config/, which images/ignition/Dockerfile
copies into the "external" collection (core inherits from it; a fresh gateway
refuses to start if core/ already exists):

  com.inductiveautomation.opcua/device/<DEV>/{config.json,resource.json}
  ignition/tag-definition/default/<folder>/.../{unary-resource.json,tags.json}

The tags come from the exports the builders write (ignition/tags/*.json).
Both PLCs share the gateway's network namespace (one Fargate task, or
network_mode: service:ignition in docker-compose.yml), so the devices point at
127.0.0.1: the ECLSS PLC on 502 and the training PLC on 5020. The formats were
captured from a gateway that created them through its own API (8.3.9).

Run from src/:  python3 tools/ignition_config.py   (build.sh runs it)
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "ignition" / "config"

# device -> (host, port, tag export holding its tags)
DEVICES = {
    "ECLSS_PLC": ("127.0.0.1", 502, "ECLSS_tags.json"),
    "TRAIN_PLC": ("127.0.0.1", 5020, "Training_tags.json"),
}

# The Modbus TCP driver's defaults, as the gateway writes them. One-based
# addressing (zeroBasedAddressing false) is why every tag address is +1.
MODBUS_TCP_DEFAULTS = {
    "advanced": {"maxRetryCount": 1, "reconnectAfterConsecutiveTimeouts": True,
                 "reverseWordOrder": False, "zeroBasedAddressing": False},
    "readRequests": {"readMultipleCoilsAllowed": True, "readMultipleDiscreteInputsAllowed": True,
                     "readMultipleRegistersRequestAllowed": True},
    "requestOptimization": {"concurrentRequests": 1, "maxCoilsPerRequest": 2000,
                            "maxDiscreteInputsPerRequest": 2000, "maxHoldingRegistersPerRequest": 125,
                            "maxHoldingRegistersPerWriteRequest": 123, "maxInputRegistersPerRequest": 125,
                            "spanGaps": True},
    "stringHandling": {"readRawStrings": False, "reverseByteOrder": False, "rightJustifyStrings": False},
    "writeRequests": {"forceMultipleRegisterWritesEnabled": False, "writeMultipleCoilsRequestAllowed": True,
                      "writeMultipleRegistersRequestAllowed": True},
}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def write_device(name, host, port):
    d = OUT / "com.inductiveautomation.opcua" / "device" / name
    settings = json.loads(json.dumps(MODBUS_TCP_DEFAULTS))
    settings["connectivity"] = {"communicationTimeout": 2000, "hostname": host, "port": port}
    dump(d / "config.json", {"profile": {"type": "ModbusTcp"}, "settings": settings})
    dump(d / "resource.json", {
        "scope": "A", "description": f"RazorHack {name}", "version": 1,
        "restricted": False, "overridable": True, "files": ["config.json"],
        "attributes": {"enabled": True}})


def write_folder(folder, parent):
    """One tag folder -> <parent>/<name>/unary-resource.json (+ tags.json for
    its atomic tags); sub-folders recurse."""
    d = parent / folder["name"]
    atoms = sorted((t for t in folder.get("tags", []) if t.get("tagType") == "AtomicTag"),
                   key=lambda t: t["name"])
    dump(d / "unary-resource.json", {
        "scope": "G", "version": 1, "restricted": False, "overridable": True,
        "files": ["tags.json"] if atoms else [], "attributes": {"config": {}}})
    if atoms:
        dump(d / "tags.json", atoms)
    for sub in folder.get("tags", []):
        if sub.get("tagType") == "Folder":
            write_folder(sub, d)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    tags_root = OUT / "ignition" / "tag-definition" / "default"
    for name, (host, port, export) in DEVICES.items():
        write_device(name, host, port)
        write_folder(json.loads((ROOT / "ignition" / "tags" / export).read_text()), tags_root)
    print("Ignition config resources:")
    print("  ignition/config/com.inductiveautomation.opcua/device/" + ", ".join(DEVICES))
    print("  ignition/config/ignition/tag-definition/default/ (ECLSS, Training)")


if __name__ == "__main__":
    main()
