#!/usr/bin/env python3
"""Split the First Boot flag into the two halves the scenario plants.

head -> Base64, the *contents* of the calibration profile (crew_setup copies it
        into NTUSER.DAT as Digester\\CalProfile)
tail -> hex, the *filename* of the profile (survives only in CREW_SETUP.EXE's
        Prefetch file-reference list; Prefetch upper-cases paths, hex survives that)

Reads the flag from ../../challenge.yml and writes <out>/profiles/<HEX>.cal.
Usage: make_profile.py <out_dir>
"""
import base64
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPLIT = "_st3p_"  # head ends with this marker, tail is the rest


def main():
    out = pathlib.Path(sys.argv[1])
    yml = (HERE / ".." / ".." / "challenge.yml").read_text()
    flag = re.search(r"^\s*-\s*(flag\{[^}\n]+\})\s*$", yml, re.M).group(1)
    i = flag.index(SPLIT) + len(SPLIT)
    head, tail = flag[:i], flag[i:]

    prof = out / "profiles"
    prof.mkdir(parents=True, exist_ok=True)
    for old in prof.glob("*.cal"):
        old.unlink()
    path = prof / (tail.encode().hex().upper() + ".cal")
    path.write_text(base64.b64encode(head.encode()).decode() + "\r\n")
    print(f"head={len(head)} chars, tail={len(tail)} chars -> {path.name}")


if __name__ == "__main__":
    main()
