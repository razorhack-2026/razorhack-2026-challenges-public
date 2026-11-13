#!/usr/bin/env python3
"""Reference solve for Hull Breach: the Cheat Engine exact-value workflow, scripted.

    solve.py ./hull_breach [EXPECTED_FLAG]

Needs an X display (run under xvfb-run), xdotool, and ptrace rights over the
child (it is our child, so Yama scope 1 allows it). Steps, mirroring Cheat Engine:

  1. First Scan: every aligned int32 == 3 in the game module's static memory
     (its .data/.bss -- what Cheat Engine lists in green as hull_breach+offset).
  2. Fly until hit, Next Scan == 2 (and == 1 if still ambiguous).
  3. Write 999 to the surviving address.
  4. Fly with auto-fire, sweeping, until the game prints the command link key.

Scanning all writable memory instead also works by hand, but some library
counters elsewhere in the process happen to count 3 -> 2 -> 1 too, and writing
to them crashes the game. A Cheat Engine player picks the green static entry.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time

def xdo(*args):
    return subprocess.run(["xdotool", *args], capture_output=True, text=True).stdout.strip()

def regions(pid):
    """Writable mappings of the game binary plus the anonymous .bss tail right after it."""
    exe = os.path.realpath(f"/proc/{pid}/exe")
    prev_end, prev_is_exe = None, False
    with open(f"/proc/{pid}/maps") as f:
        for line in f:
            parts = line.split()
            lo, hi = (int(x, 16) for x in parts[0].split("-"))
            path = parts[5] if len(parts) > 5 else ""
            is_exe = path == exe
            bss_tail = not path and prev_is_exe and lo == prev_end
            if parts[1].startswith("rw") and (is_exe or bss_tail):
                yield lo, hi
            prev_end, prev_is_exe = hi, is_exe

def first_scan(pid, value):
    want = struct.pack("<i", value)
    hits = []
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        for lo, hi in regions(pid):
            try:
                mem.seek(lo)
                data = mem.read(hi - lo)
            except OSError:
                continue
            for m in re.finditer(re.escape(want), data):
                if m.start() % 4 == 0:
                    hits.append(lo + m.start())
    return hits

def read_i32(mem, addr):
    mem.seek(addr)
    return struct.unpack("<i", mem.read(4))[0]

def next_scan(pid, addrs, value):
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        return [a for a in addrs if read_i32(mem, a) == value]

def write_i32(pid, addr, value):
    with open(f"/proc/{pid}/mem", "r+b", 0) as mem:
        mem.seek(addr)
        mem.write(struct.pack("<i", value))
        return read_i32(mem, addr)

def main():
    binary = sys.argv[1]
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    proc = subprocess.Popen([binary], stdout=subprocess.PIPE, text=True)
    result = []
    threading.Thread(target=lambda: result.extend(proc.stdout), daemon=True).start()

    wid = xdo("search", "--sync", "--name", "Hull Breach").splitlines()[0]
    xdo("windowfocus", "--sync", wid)
    time.sleep(0.5)

    cands = first_scan(proc.pid, 3)
    print(f"[1] first scan int32 == 3: {len(cands)} hits")
    # launch: hold Space for a few frames (raylib misses a press+release
    # that lands inside one frame, which is what `xdotool key` sends)
    xdo("keydown", "space")
    time.sleep(0.1)
    xdo("keyup", "space")

    # Wait for the first curtain hit (hull 3 -> 2); hull then holds for the
    # invulnerability window, so a second read 0.3 s later filters transients.
    deadline = time.time() + 15
    while time.time() < deadline:
        two = next_scan(proc.pid, cands, 2)
        if two:
            time.sleep(0.3)
            two = next_scan(proc.pid, two, 2)
            if two:
                break
        time.sleep(0.05)
    print(f"[2] next scan == 2: {len(two)} hits")
    cands = two
    if len(cands) > 1:
        deadline = time.time() + 15
        while time.time() < deadline and len(cands) > 1:
            one = next_scan(proc.pid, cands, 1)
            if one:
                time.sleep(0.3)
                cands = next_scan(proc.pid, one, 1) or cands
            time.sleep(0.05)
        print(f"[2b] next scan == 1: {len(cands)} hits")
    if len(cands) != 1:
        print("hull address not isolated", file=sys.stderr)
        proc.kill()
        return 1
    hull = cands[0]
    print(f"[3] hull at {hull:#x}, wrote 999 -> reads back {write_i32(proc.pid, hull, 999)}")

    # Fly: hold fire, sweep side to side, top the hull back up if it runs low.
    # Full wall-to-wall passes (1.7 s crosses the screen). Shorter sweeps drift
    # into the band the left wall clamps them to and can strand the last drone
    # at the far right.
    xdo("keydown", "space")
    side = "Left"
    deadline = time.time() + 300
    while time.time() < deadline and not any(l.startswith("COMMAND") for l in result):
        xdo("keydown", side)
        time.sleep(1.9)
        xdo("keyup", side)
        side = "Right" if side == "Left" else "Left"
        with open(f"/proc/{proc.pid}/mem", "rb", 0) as mem:
            if read_i32(mem, hull) < 500:
                write_i32(proc.pid, hull, 999)
    xdo("keyup", "space")

    line = next((l.strip() for l in result if l.startswith("COMMAND")), "")
    print(f"[4] game says: {line or '(nothing, timed out)'}")
    if shutil.which("import"):                # optional end screenshot (ImageMagick)
        subprocess.run(["import", "-window", "root", "/tmp/hull_breach_end.png"], capture_output=True)
    proc.kill()
    if expected is not None:
        ok = line == f"COMMAND LINK KEY: {expected}"
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0 if line.startswith("COMMAND LINK KEY:") else 1

if __name__ == "__main__":
    sys.exit(main())
