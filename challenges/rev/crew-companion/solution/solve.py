#!/usr/bin/env python3
"""Crew Companion -- reference solver (GM-only).

Works from the competitor download only: decompiles dist/crew-companion.apk with
jadx, reads the door-code check and revealDoorCodes() out of the decompiled
source, pulls the three Base64 parts from wherever the method says they live, and
decodes them in the method's order. Nothing is hardcoded and nothing in src/ is read.

  python3 solution/solve.py [path/to/crew-companion.apk]

Needs jadx on PATH (brew install jadx) and Java 11+.
"""
import base64
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APK = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "dist" / "crew-companion.apk"


def main() -> int:
    with tempfile.TemporaryDirectory() as out:
        subprocess.run(["jadx", "-q", "-d", out, str(APK)], check=True)
        out = Path(out)
        act = next(out.glob("sources/**/MainActivity.java")).read_text()
        pkg = act.split("package ", 1)[1].split(";", 1)[0]
        build_config = (out / "sources" / Path(*pkg.split(".")) / "BuildConfig.java").read_text()
        manifest = (out / "resources" / "AndroidManifest.xml").read_text()
        strings = (out / "resources" / "res" / "values" / "strings.xml").read_text()

    # 1. the gate: input reversed must equal a constant, so the code is that constant reversed
    check = re.search(r"reverse\(\)\.toString\(\)\.equals\((\w+)\)", act).group(1)
    constant = re.search(rf'{check} = "([^"]+)"', act).group(1)
    print(f"access code: {constant[::-1]}")

    # 2. revealDoorCodes(): the join order and where each piece comes from
    join = re.search(r"String revealDoorCodes\(\) \{\s*String \w+ = (.+?);", act, re.S).group(1)
    parts = []
    for term in (t.strip() for t in join.split("+")):
        if m := re.fullmatch(r"getString\(R\.string\.(\w+)\)", term):
            parts.append(re.search(rf'<string name="{m.group(1)}">([^<]+)</string>', strings).group(1))
        elif m := re.fullmatch(r"BuildConfig\.(\w+)", term):
            parts.append(re.search(rf'{m.group(1)} = "([^"]+)"', build_config).group(1))
        elif m := re.fullmatch(r"(\w+)\(\)", term):
            # a helper: find the meta-data key it reads, then its value in the manifest
            helper = re.search(rf"String {m.group(1)}\(\) \{{(.+?)\n    \}}", act, re.S).group(1)
            key = re.search(r'getString\("([^"]+)"', helper).group(1)
            parts.append(re.search(rf'android:name="{re.escape(key)}"\s+android:value="([^"]+)"', manifest).group(1))
        else:
            raise SystemExit(f"unexpected term in revealDoorCodes: {term}")
    print("parts, in join order:", parts)
    print(base64.b64decode("".join(parts)).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
