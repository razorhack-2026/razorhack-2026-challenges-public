# /// script
# requires-python = ">=3.10"
# dependencies = ["dissect.util>=3.18", "regipy>=4.0"]
# ///
"""First Boot solver -- works from dist/first-boot-artifacts.zip alone.

1. Prefetch: decompress every .pf (Win10+ MAM / LZXPRESS-Huffman), find the
   executable that ran from a volume other than the system volume
   (CREW_SETUP.EXE, off the ONBOARD stick), and read its file-reference list.
   The calibration profile it opened has a hex filename = the flag's tail.
2. NTUSER.DAT: the key crew_setup wrote around that run time,
   Software\\KOT\\WasteSystems\\Digester, holds CalProfile = Base64 of the head.

Usage: uv run solution/solve.py dist/first-boot-artifacts.zip
"""
import base64
import datetime as dt
import pathlib
import re
import struct
import sys
import tempfile
import zipfile

from dissect.util.compression import lzxpress_huffman
from regipy.registry import RegistryHive


def filetime(v):
    return dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(microseconds=v // 10)


def parse_pf(raw):
    if raw[:3] == b"MAM":
        size = struct.unpack_from("<I", raw, 4)[0]
        raw = lzxpress_huffman.decompress(raw[8:])[:size]
    assert raw[4:8] == b"SCCA", "not a prefetch file"
    exe = raw[0x10:0x4C].decode("utf-16-le").split("\0")[0]
    off, size = struct.unpack_from("<II", raw, 0x64)
    names = [n for n in raw[off:off + size].decode("utf-16-le").split("\0") if n]
    last_run = filetime(struct.unpack_from("<Q", raw, 0x80)[0])
    return exe, names, last_run


def main():
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(sys.argv[1]).extractall(tmp)
        root = pathlib.Path(tmp)

        # The system volume is wherever \WINDOWS\SYSTEM32\ lives in the traces.
        runs = [parse_pf(p.read_bytes()) for p in root.rglob("*.pf")]
        sysvol = next(re.match(r"(\\VOLUME\{[^}]+\})\\WINDOWS\\", n).group(1)
                      for _, names, _ in runs for n in names if re.match(r"\\VOLUME\{[^}]+\}\\WINDOWS\\", n))
        off_volume = [(exe, names, t) for exe, names, t in runs
                      if any(n.endswith("\\" + exe) and not n.startswith(sysvol) for n in names)]
        for exe, _, t in off_volume:
            print(f"[prefetch] ran from a non-system volume: {exe}  last run {t:%Y-%m-%d %H:%M:%S} UTC")

        exe, names, t = next(r for r in off_volume if r[0] == "CREW_SETUP.EXE")
        cal = next(n for n in names if n.endswith(".CAL"))
        print(f"[prefetch] {exe} opened {cal}")
        tail = bytes.fromhex(cal.rsplit("\\", 1)[1][:-4]).decode()

        hive = RegistryHive(str(next(root.rglob("NTUSER.DAT"))))
        path = r"\Software\KOT\WasteSystems\Digester"
        key = hive.get_key(path)
        vals = {v.name: v.value for v in key.iter_values()}
        print(f"[NTUSER]   {path} last written {filetime(key.header.last_modified):%Y-%m-%d %H:%M:%S} UTC: {vals}")
        head = base64.b64decode(vals["CalProfile"]).decode()

    flag = head + tail
    assert re.fullmatch(r"flag\{[^}]+\}", flag), flag
    print(flag)


if __name__ == "__main__":
    main()
