#!/usr/bin/env python3
"""Reference solve for Fried Readout: the Cheat Engine unknown-value workflow, scripted.

    solve.py ./fried_readout [EXPECTED_FLAG]

Needs an X display (run under xvfb-run), xdotool, and ptrace rights over the
child (it is our child, so Yama scope 1 allows it). Steps, mirroring Cheat Engine
with value type Float:

  1. First Scan, Unknown initial value: snapshot every aligned float32 in the
     game module's static memory (its .data/.bss -- what Cheat Engine lists in
     green as fried_readout+offset) on the launch screen.
  2. Rounds: fire at the Harvester, stop, let the bullets clear, then Next Scan
     "Decreased value"; wait without firing, then Next Scan "Unchanged value".
     Repeat until one address keeps dropping on every volley and stays put
     between them (see the comment in main() on how a blind sweep scores it).
  3. Write 1.0 to it.
  4. Fly with auto-fire, sweeping, until the game prints the command link key.
"""
import array
import os
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

def snapshot(pid):
    """{address: float32} for every aligned 4-byte slot in the module's static memory."""
    snap = {}
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        for lo, hi in regions(pid):
            try:
                mem.seek(lo)
                vals = array.array("f", mem.read(hi - lo))
            except OSError:
                continue
            for i, v in enumerate(vals):
                snap[lo + 4 * i] = v
    return snap

def read_f32(mem, addr):
    mem.seek(addr)
    return array.array("f", mem.read(4))[0]

def write_f32(pid, addr, value):
    with open(f"/proc/{pid}/mem", "r+b", 0) as mem:
        mem.seek(addr)
        mem.write(array.array("f", [value]).tobytes())
        return read_f32(mem, addr)

def hold(key, secs):
    xdo("keydown", key)
    time.sleep(secs)
    xdo("keyup", key)

def volley():
    """Fire through one full edge-to-edge pass (1.7 s crosses the screen), so the
    ship passes under the Harvester wherever it is, and ends at the right edge
    every time -- otherwise PD-1's own x shows up as a value that drops per volley."""
    hold("Left", 1.8)
    xdo("keydown", "space")
    hold("Right", 1.8)
    xdo("keyup", "space")

def main():
    binary = sys.argv[1]
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    proc = subprocess.Popen([binary], stdout=subprocess.PIPE, text=True)
    result = []
    threading.Thread(target=lambda: result.extend(proc.stdout), daemon=True).start()

    wid = xdo("search", "--sync", "--name", "Fried Readout").splitlines()[0]
    xdo("windowfocus", "--sync", wid)
    time.sleep(0.5)

    prev = snapshot(proc.pid)
    cands = {a for a, v in prev.items() if v == v}           # drop NaN slots
    drops = dict.fromkeys(cands, 0)
    print(f"[1] first scan, unknown initial float: {len(cands)} slots")
    hold("space", 0.1)                                       # launch (hold: raylib misses 1-frame taps)

    # A blind sweep can miss the Harvester in a given volley, where a player
    # aiming at it would not, so rather than demand a drop every round, keep
    # everything that never rises or moves while idle, and pick the slot that
    # dropped in the most volleys, once it leads every other slot by two.
    # One-off drops (an escort's alive flag going 1 -> 0) and occasional ones
    # (a dead bullet's last y, which sometimes ends lower than last time) fall
    # behind; a player reading the values in Cheat Engine rejects those anyway.
    t0 = time.time()
    found = None
    for rnd in range(1, 11):
        volley()
        time.sleep(1.2)                                      # bullets in flight land or leave
        now = snapshot(proc.pid)
        cands = {a for a in cands if now.get(a, prev[a]) <= prev[a]}
        for a in cands:
            drops[a] += now[a] < prev[a]
        time.sleep(0.8)
        idle = snapshot(proc.pid)
        cands = {a for a in cands if idle[a] == now[a]}
        prev = idle
        ranked = sorted(cands, key=lambda a: drops[a], reverse=True)
        best, second = drops[ranked[0]], drops[ranked[1]]
        print(f"[2.{rnd}] still unchanged-while-idle: {len(cands)}; most drops {best} "
              f"(value {idle[ranked[0]]:.1f}), next {second}, t={time.time() - t0:.1f}s")
        if best >= 4 and best - second >= 2:
            found = ranked[0]
            break
    if found is None:
        print("integrity address not isolated", file=sys.stderr)
        proc.kill()
        return 1
    print(f"[3] integrity at {found:#x} = {prev[found]:.1f}, wrote 1.0 -> reads back "
          f"{write_f32(proc.pid, found, 1.0)}")

    xdo("keydown", "space")
    side = "Left"
    deadline = time.time() + 120
    while time.time() < deadline and not any(l.startswith("COMMAND") for l in result):
        hold(side, 1.1)
        side = "Right" if side == "Left" else "Left"
    xdo("keyup", "space")

    line = next((l.strip() for l in result if l.startswith("COMMAND")), "")
    print(f"[4] game says: {line or '(nothing, timed out)'} at t={time.time() - t0:.1f}s")
    subprocess.run(["import", "-window", "root", "/tmp/fried_readout_end.png"], capture_output=True)
    proc.kill()
    if expected is not None:
        ok = line == f"COMMAND LINK KEY: {expected}"
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0 if line.startswith("COMMAND LINK KEY:") else 1

if __name__ == "__main__":
    sys.exit(main())
