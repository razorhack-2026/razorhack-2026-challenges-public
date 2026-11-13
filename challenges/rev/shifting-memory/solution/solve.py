#!/usr/bin/env python3
"""Reference solve for Shifting Memory: the Cheat Engine pointer-scan workflow, scripted.

    solve.py ./shifting_memory [EXPECTED_FLAG]

Needs an X display (run under xvfb-run), xdotool, and ptrace rights over the
child (it is our child, so Yama scope 1 allows it). Steps, mirroring Cheat Engine:

  1. Find the hull where it lives right now: an int32 on the heap that drops by
     exactly 1 when PD-1 is hit (Cheat Engine: Exact Value 5, take a hit, Next
     Scan 4, before the BANK number on the HUD changes). The player struct is
     a small malloc, so it is in [heap].
  2. Pointer scan for that address, level 1: a pointer-sized slot in the game
     module's static memory (green in Cheat Engine) that holds an address just
     below it, giving base + offset.
  3. Wait for the next move (the BANK number ticks over) and keep the pointer
     whose value changed and still leads to a sane hull.
  4. Freeze 999 through the pointer (re-read the pointer, write the hull, on a
     timer, the way Cheat Engine freezes a pointer entry) and fly with
     auto-fire until the game prints the command link key.
"""
import array
import os
import re
import struct
import subprocess
import sys
import threading
import time

MAX_OFFSET = 0x100      # Cheat Engine's pointer scan default max offset is larger; the struct is small

def xdo(*args):
    return subprocess.run(["xdotool", *args], capture_output=True, text=True).stdout.strip()

def maps(pid):
    with open(f"/proc/{pid}/maps") as f:
        for line in f:
            parts = line.split()
            lo, hi = (int(x, 16) for x in parts[0].split("-"))
            yield lo, hi, parts[1], parts[5] if len(parts) > 5 else ""

def static_regions(pid):
    """Writable mappings of the game binary plus the anonymous .bss tail right after it."""
    exe = os.path.realpath(f"/proc/{pid}/exe")
    prev_end, prev_is_exe = None, False
    for lo, hi, perm, path in maps(pid):
        is_exe = path == exe
        bss_tail = not path and prev_is_exe and lo == prev_end
        if perm.startswith("rw") and (is_exe or bss_tail):
            yield lo, hi
        prev_end, prev_is_exe = hi, is_exe

def heap_regions(pid):
    return [(lo, hi) for lo, hi, perm, path in maps(pid) if path == "[heap]" and perm.startswith("rw")]

def small_ints(pid):
    """{address: value} for every aligned int32 on the heap with a value 1..5."""
    found = {}
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        for lo, hi in heap_regions(pid):
            mem.seek(lo)
            data = mem.read(hi - lo)
            for v in range(1, 6):
                for m in re.finditer(re.escape(struct.pack("<i", v)), data):
                    if m.start() % 4 == 0:
                        found[lo + m.start()] = v
    return found

def pointers_to(pid, addr):
    """Static 8-byte slots holding an address in [addr - MAX_OFFSET, addr]: (slot, offset)."""
    hits = []
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        for lo, hi in static_regions(pid):
            mem.seek(lo)
            vals = array.array("Q", mem.read(hi - lo))
            for i, v in enumerate(vals):
                if 0 <= addr - v < MAX_OFFSET:
                    hits.append((lo + 8 * i, addr - v))
    return hits

def read_q(mem, addr):
    mem.seek(addr)
    return struct.unpack("<Q", mem.read(8))[0]

def read_i32(mem, addr):
    mem.seek(addr)
    return struct.unpack("<i", mem.read(4))[0]

def hold(key, secs):
    xdo("keydown", key)
    time.sleep(secs)
    xdo("keyup", key)

def main():
    binary = sys.argv[1]
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    proc = subprocess.Popen([binary], stdout=subprocess.PIPE, text=True)
    result = []
    threading.Thread(target=lambda: result.extend(proc.stdout), daemon=True).start()
    pid = proc.pid

    wid = xdo("search", "--sync", "--name", "Shifting Memory").splitlines()[0]
    xdo("windowfocus", "--sync", wid)
    time.sleep(0.5)

    hold("space", 0.1)                                       # launch (hold: raylib misses 1-frame taps)
    t0 = time.time()
    # 1-2: sit still; on every hit some heap int drops by exactly 1. Keep the
    # ones a static pointer leads to.
    prev, cands = small_ints(pid), []
    while not cands and time.time() - t0 < 20:
        time.sleep(0.05)
        now = small_ints(pid)
        for a, v in now.items():
            if prev.get(a) == v + 1:
                cands += [(p, off) for p, off in pointers_to(pid, a)]
        prev = now
    print(f"[1-2] hull found at t={time.time() - t0:.1f}s; static pointers to it: "
          + ", ".join(f"{p:#x}+{off:#x}" for p, off in cands))
    if not cands:
        print("no hull/pointer found", file=sys.stderr)
        proc.kill()
        return 1

    # 3: across a move the right pointer changes value and still reads a hull 1..5.
    # Moves happen every 3 s of game time, so poll for the first change.
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        before = {c: read_q(mem, c[0]) for c in cands}
        deadline = time.time() + 4
        while time.time() < deadline and all(read_q(mem, c[0]) == before[c] for c in cands):
            time.sleep(0.05)
        good = [c for c in cands if read_q(mem, c[0]) != before[c]
                and 0 <= read_i32(mem, read_q(mem, c[0]) + c[1]) <= 5]
    print(f"[3] after a move: {len(good)} pointer(s) followed it: "
          + ", ".join(f"{p:#x}+{off:#x}" for p, off in good))
    if len(good) != 1:
        proc.kill()
        return 1
    ptr, off = good[0]

    # 4: freeze through the pointer.
    stop = threading.Event()
    def freezer():
        with open(f"/proc/{pid}/mem", "r+b", 0) as mem:
            while not stop.is_set():
                mem.seek(read_q(mem, ptr) + off)
                mem.write(struct.pack("<i", 999))
                time.sleep(0.02)
    threading.Thread(target=freezer, daemon=True).start()
    print("[4] frozen through the pointer; flying")

    hold("r", 0.1)                                           # relaunch if PD-1 was lost (ignored in play)
    hold("space", 0.1)
    xdo("keydown", "space")
    side = "Left"
    deadline = time.time() + 300
    while time.time() < deadline and not any(l.startswith("COMMAND") for l in result):
        # Full wall-to-wall passes (1.7 s crosses the screen). Shorter sweeps
        # drift into the band the left wall clamps them to and can strand the
        # last drone at the far right.
        hold(side, 1.9)
        side = "Right" if side == "Left" else "Left"
    xdo("keyup", "space")
    stop.set()

    line = next((l.strip() for l in result if l.startswith("COMMAND")), "")
    print(f"[5] game says: {line or '(nothing, timed out)'} at t={time.time() - t0:.1f}s")
    subprocess.run(["import", "-window", "root", "/tmp/shifting_memory_end.png"], capture_output=True)
    proc.kill()
    if expected is not None:
        ok = line == f"COMMAND LINK KEY: {expected}"
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0 if line.startswith("COMMAND LINK KEY:") else 1

if __name__ == "__main__":
    sys.exit(main())
