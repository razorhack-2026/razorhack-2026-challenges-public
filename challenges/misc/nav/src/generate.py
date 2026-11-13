#!/usr/bin/env python3
"""NAV artifact generator. Writes dist/nav_log.txt.

Edit COORD to relocate the star fix. Everything else derives from it: segment E
is the base64 payload players decode, and the flag is the decoded string.
Flag: flag{n4v_<COORD>}
"""
import base64
import os

COORD = "n4v_36.0659,-94.1737"

TEMPLATE = """# NAV LOG - KEEPER OF TOMORROW - MISSION DAY 441
# STATUS: CORRUPTED BY UNKNOWN AGENTS
# NOTE FROM SYSOP: "This planet has 64 hours in a day to ROT away"

[SEGMENT A - ROUTE HEADER]
EBG13 guvf vf abg gur pbbeqvangr

[SEGMENT B - STAR FIX 1]
U2FsdGVkX1+abc123fakepadding==   # archived route record

[SEGMENT C - ERROR TELEMETRY]
ERR_NAV_001: offset=0x2A
ERR_NAV_002: offset=0x11
ERR_NAV_003: offset=0x37

[SEGMENT D - CAPTAIN NOTE]
"Three offsets XOR'd is the old mapping. Since the refit the fix ships plain:
 decode segment E and read it verbatim, comma and sign included."

[SEGMENT E - ENCODED FIX BLOB]
{blob}   # base64
"""


def flag_for(coord: str) -> str:
    return f"flag{{n4v_{coord}}}"


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    os.makedirs(out_dir, exist_ok=True)
    blob = base64.b64encode(COORD.encode()).decode()
    out_path = os.path.join(out_dir, "nav_log.txt")
    with open(out_path, "w") as f:
        f.write(TEMPLATE.format(blob=blob))
    print(f"wrote dist/nav_log.txt (blob: {blob})")
    print(f"flag: {flag_for(COORD)}")


if __name__ == "__main__":
    main()
