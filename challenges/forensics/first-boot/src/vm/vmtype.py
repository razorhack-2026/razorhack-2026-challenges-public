#!/usr/bin/env python3
"""vmtype.py -- type a string into a Proxmox VM's console with `qm sendkey` (run on the host).

Usage: vmtype.py <vmid> <text> [--enter]   e.g.  vmtype.py 404 'E:\\crew_setup.exe' --enter
Covers letters, digits, space and the punctuation used by the First Boot scenario.
"""
import subprocess
import sys
import time

SPECIAL = {" ": "spc", "\\": "backslash", ".": "dot", "-": "minus", "/": "slash", ",": "comma",
           ";": "semicolon", "'": "apostrophe", "=": "equal",
           ":": "shift-semicolon", "_": "shift-minus", '"': "shift-apostrophe", "$": "shift-4", "(": "shift-9", ")": "shift-0", "*": "shift-8"}


def key(c):
    if c.isdigit() or c.islower():
        return c
    if c.isupper():
        return "shift-" + c.lower()
    return SPECIAL[c]


def main():
    vmid, text = sys.argv[1], sys.argv[2]
    for c in text:
        subprocess.run(["qm", "sendkey", vmid, key(c)], check=True)
        time.sleep(0.05)
    if "--enter" in sys.argv[3:]:
        subprocess.run(["qm", "sendkey", vmid, "ret"], check=True)


if __name__ == "__main__":
    main()
