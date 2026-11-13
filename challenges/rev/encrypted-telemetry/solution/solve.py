#!/usr/bin/env python3
"""Reference solve for Encrypted Telemetry: the Cheat Engine changed/unchanged workflow, scripted.

    solve.py ./encrypted_telemetry [EXPECTED_FLAG]

Needs an X display (run under xvfb-run), xdotool, and ptrace rights over the
child (it is our child, so Yama scope 1 allows it). Steps, mirroring Cheat Engine
with value type 4 Bytes:

  1. First Scan, Unknown initial value: snapshot every aligned 4-byte slot in
     the game module's static memory (its .data/.bss -- what Cheat Engine lists
     in green as encrypted_telemetry+offset) on the launch screen.
  2. Next Scan "Unchanged value" while flying before the first hit can land,
     which drops everything that moves on its own (timers, drones, bullets).
  3. Keep flying, still and without firing, and sample at 20 Hz. A Cheat Engine
     player scans "Changed value" right after each hit and "Unchanged value"
     between hits; here the same filter is applied afterwards: keep the slots
     that change in a few separate samples and never in two running, and take
     the largest group that changed in exactly the same samples -- the hits.
     That leaves the stored hull and its damage-log look-alikes.
  4. Freeze all of them at their First Scan value (the hull's is "5", encrypted)
     and fly with auto-fire until the game prints the command link key.
     Freezing the look-alikes does nothing; a player freezes them one by one
     and watches which one pins the HUD.
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
    """{address: uint32} for every aligned 4-byte slot in the module's static memory."""
    snap = {}
    with open(f"/proc/{pid}/mem", "rb", 0) as mem:
        for lo, hi in regions(pid):
            try:
                mem.seek(lo)
                vals = array.array("I", mem.read(hi - lo))
            except OSError:
                continue
            for i, v in enumerate(vals):
                snap[lo + 4 * i] = v
    return snap

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

    wid = xdo("search", "--sync", "--name", "Encrypted Telemetry").splitlines()[0]
    xdo("windowfocus", "--sync", wid)
    time.sleep(0.5)

    first = snapshot(proc.pid)
    print(f"[1] first scan, unknown initial 4 bytes: {len(first)} slots")
    hold("space", 0.1)                                       # launch (hold: raylib misses 1-frame taps)
    t0 = time.time()

    # The first drone shots need about 3.5 s to reach PD-1, so 0.5-2.5 s is hit-free.
    time.sleep(0.5)
    base = snapshot(proc.pid)
    while time.time() - t0 < 2.5:
        time.sleep(0.1)
        now = snapshot(proc.pid)
        base = {a: v for a, v in base.items() if now[a] == v}
    cands = set(base)
    print(f"[2] unchanged before the first hit: {len(cands)}")

    # Sit still and don't fire, so only hits change anything that is left.
    # Each hit moves the stored hull to a value it has never held before; an
    # enemy bullet's slot also changes in two samples, but goes 0 -> live -> 0.
    samples, prev = [], base
    seen = {a: [base[a]] for a in cands}
    while time.time() - t0 < 7.5:
        time.sleep(0.05)
        now = snapshot(proc.pid)
        moved = {a for a in cands if now[a] != prev[a]}
        for a in moved:
            seen[a].append(now[a])
        samples.append(moved)
        prev = now
    hold("p", 0.1)                                           # pause while we look
    changed_at = {a: tuple(i for i, s in enumerate(samples) if a in s) for a in cands}
    groups = {}
    for a, sig in changed_at.items():
        if (2 <= len(sig) <= 10 and all(j - i > 1 for i, j in zip(sig, sig[1:]))
                and len(set(seen[a])) == len(seen[a])):
            groups.setdefault(sig, []).append(a)
    if not groups:
        print("no hit signature found", file=sys.stderr)
        proc.kill()
        return 1
    sig, found = max(groups.items(), key=lambda kv: len(kv[1]))
    print(f"[3] {len(found)} slots changed on exactly the same {len(sig)} hits:")
    for a in sorted(found):
        print(f"      {a:#x}  first {first[a]:#010x}  now {prev[a]:#010x}")

    # Freeze them all at the First Scan value, the way Cheat Engine re-writes a
    # frozen entry on a timer.
    frozen = [(a, array.array("I", [first[a]]).tobytes()) for a in found]
    stop = threading.Event()
    def freezer():
        with open(f"/proc/{proc.pid}/mem", "r+b", 0) as mem:
            while not stop.is_set():
                for a, b in frozen:
                    mem.seek(a)
                    mem.write(b)
                time.sleep(0.02)
    threading.Thread(target=freezer, daemon=True).start()
    print("[4] frozen; flying")

    hold("p", 0.1)                                           # unpause (ignored if PD-1 was already lost)
    hold("r", 0.1)                                           # relaunch if it was (ignored in play)
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
    subprocess.run(["import", "-window", "root", "/tmp/encrypted_telemetry_end.png"], capture_output=True)
    proc.kill()
    if expected is not None:
        ok = line == f"COMMAND LINK KEY: {expected}"
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0 if line.startswith("COMMAND LINK KEY:") else 1

if __name__ == "__main__":
    sys.exit(main())
