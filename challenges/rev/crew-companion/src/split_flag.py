#!/usr/bin/env python3
"""Split a flag into the three Base64 parts Crew Companion stores (GM build helper).

  python3 src/split_flag.py 'flag{...}'

Prints the three parts and where each one goes. revealDoorCodes() joins them
manifest -> strings.xml -> BuildConfig and Base64-decodes the result, so the
order here must match MainActivity.
"""
import base64
import sys

flag = sys.argv[1]
b = base64.b64encode(flag.encode()).decode()
third = -(-len(b) // 3)
a, s, c = b[:third], b[third:2 * third], b[2 * third:]
assert base64.b64decode(a + s + c).decode() == flag
print(f"AndroidManifest.xml  <meta-data android:name=\"rpc.kot.uplink_tag\" android:value=\"{a}\"/>")
print(f"res/values/strings.xml  <string name=\"deck_key\">{s}</string>")
print(f"app/build.gradle  buildConfigField \"String\", \"SHIFT_SIG\", '\"{c}\"'")
