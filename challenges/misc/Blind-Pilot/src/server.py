#!/usr/bin/env python3
"""
BLIND PILOT - CTF challenge server (see README.md for rules and deployment).

Run modes:
    python3 server.py                 one game on stdin/stdout (socat, xinetd, ynetd)
    python3 server.py --listen 1337   built-in TCP server, one game per connection
"""
import os
import re
import secrets
import socketserver
import sys
import time

# ---------------------------------------------------------------- settings
GRID = int(os.environ.get("GRID", 16))            # field is GRID^3 cells
DENSITY = float(os.environ.get("DENSITY", 0.22))  # fraction of cells with an asteroid
HULL = int(os.environ.get("HULL", 5))             # hull points; each impact costs one
SCAN_RANGE = int(os.environ.get("SCAN_RANGE", 1)) # 1 = the 26 neighbours; 2 removes the blind spot
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 90))     # seconds per connection
MAX_COMMANDS = int(os.environ.get("MAX_COMMANDS", 8000)) # commands per connection
SAFE_RADIUS = 2   # no asteroids start this close (Chebyshev) to the start cell

DIRS = {
    "right":    (1, 0, 0),
    "left":     (-1, 0, 0),
    "forward":  (0, 1, 0),
    "backward": (0, -1, 0),
    "up":       (0, 0, 1),
    "down":     (0, 0, -1),
}
DIR_NAME = {v: k for k, v in DIRS.items()}

SCAN_RE = re.compile(r"^scan\s+(-?\d+)\s*,?\s*(-?\d+)\s*,?\s*(-?\d+)$")

HELP = """FLIGHT MANUAL
Reach the jump gate in the far corner of the field.

Commands:
  move <left|right|forward|backward|up|down>   fly one cell; time advances one tick
  scan <dx>,<dy>,<dz>                          inspect a nearby cell; time does not advance
  status                                       tick, position, hull, gate
  help                                         this manual

Axes: x = right(+)/left(-)   y = forward(+)/backward(-)   z = up(+)/down(-)

Each tick:
  1. your ship moves; flying into a cell that holds an asteroid is an impact
  2. every asteroid drifts one cell along its heading; one landing on you is an impact
Asteroids never turn, except at the edge of the field, where they bounce: the
heading reverses and the asteroid moves one cell back the way it came.
Each impact costs one hull point. At zero hull the ship is lost."""

BANNER = """
--- BLIND PILOT ---
RazerPowerCo navigation systems offline. Manual flight controls active.
"""


def load_flag():
    if os.environ.get("FLAG"):
        return os.environ["FLAG"]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flag.txt")
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return "SPACE{test_flag_not_configured}"


def drift(pos, v, n):
    """One tick of asteroid motion, bouncing off the edge of the field."""
    nxt = tuple(p + o for p, o in zip(pos, v))
    if not all(0 <= c < n for c in nxt):
        v = tuple(-c for c in v)
        nxt = tuple(p + o for p, o in zip(pos, v))
    return nxt, v


class Field:
    """Game state. Kept free of I/O so it can be tested and simulated directly."""

    def __init__(self, n=GRID, density=DENSITY, hull=HULL, rng=None):
        self.n = n
        self.rng = rng or secrets.SystemRandom()
        self.ship = (0, 0, 0)
        self.goal = (n - 1, n - 1, n - 1)
        self.hull = hull
        self.tick = 0
        self.asteroids = []   # list of [x, y, z, (vx, vy, vz)]
        self._spawn(density)

    def _spawn(self, density):
        n = self.n
        count = int(n ** 3 * density)
        vels = list(DIRS.values())
        taken = set()
        while len(self.asteroids) < count:
            p = (self.rng.randrange(n), self.rng.randrange(n), self.rng.randrange(n))
            if p in taken or max(abs(c) for c in p) <= SAFE_RADIUS:
                continue
            taken.add(p)
            self.asteroids.append([*p, self.rng.choice(vels)])

    def in_bounds(self, p):
        return all(0 <= c < self.n for c in p)

    def at(self, p):
        """Velocities of every asteroid currently in cell p."""
        return [a[3] for a in self.asteroids if (a[0], a[1], a[2]) == p]

    def scan(self, d):
        p = tuple(s + o for s, o in zip(self.ship, d))
        if not self.in_bounds(p):
            return None  # out of bounds
        return self.at(p)

    def move(self, d):
        """Advance one tick. Returns number of impacts this tick."""
        impacts = 0
        nx = tuple(s + o for s, o in zip(self.ship, d))
        self.ship = nx
        impacts += len(self.at(nx))              # flew into an asteroid
        for a in self.asteroids:
            pos, a[3] = drift((a[0], a[1], a[2]), a[3], self.n)
            a[0], a[1], a[2] = pos
        # every asteroid moved, so anything in our cell now arrived this tick
        impacts += len(self.at(nx))              # asteroid drifted into the ship
        self.hull -= impacts
        self.tick += 1
        return impacts


def fmt_vel(v):
    return DIR_NAME[v]


def run_game(rfile, wfile, flag):
    """Play one game over a pair of text streams."""
    def out(msg=""):
        wfile.write(msg + "\n")
        wfile.flush()

    field = Field()
    start = time.monotonic()
    commands = 0

    out(BANNER)
    out("NAV-COMPUTER OFFLINE. MANUAL PILOTING ENGAGED.")
    out(f"Asteroid field is {field.n}x{field.n}x{field.n}. Coordinates are (x, y, z).")
    out(f"Ship position: {field.ship}   Jump gate: {field.goal}")
    out(f"Radar range: {SCAN_RANGE} cell(s) on each axis. Scans take no time.")
    out(f"Deflector shields can absorb {field.hull - 1} impact(s). The next one is fatal.")
    out(f"You have {int(TIME_LIMIT)} seconds before life support fails.")
    out("Type 'help' for the flight manual.")

    while True:
        wfile.write("> ")
        wfile.flush()
        line = rfile.readline()
        if not line:
            return
        line = line.strip().lower()
        if not line:
            continue

        commands += 1
        if time.monotonic() - start > TIME_LIMIT:
            out("LIFE SUPPORT FAILURE. The crew did not survive the journey.")
            return
        if commands > MAX_COMMANDS:
            out("REACTOR DEPLETED. The ship drifts silently into the dark.")
            return

        if line == "help":
            out(HELP)
            continue

        if line == "status":
            out(f"tick={field.tick} position={field.ship} hull={field.hull} goal={field.goal}")
            continue

        m = SCAN_RE.match(line)
        if m:
            d = tuple(int(g) for g in m.groups())
            if any(abs(c) > SCAN_RANGE for c in d) or d == (0, 0, 0):
                out(f"ERROR: scan offsets must each be between -{SCAN_RANGE} and {SCAN_RANGE} (and not all 0)")
                continue
            res = field.scan(d)
            label = f"({d[0]},{d[1]},{d[2]})"
            if res is None:
                out(f"{label} out of bounds")
            elif not res:
                out(f"{label} empty")
            else:
                out(f"{label} asteroid " + " ".join(f"moving {fmt_vel(v)}" for v in res))
            continue

        if line.startswith("move"):
            parts = line.split()
            if len(parts) != 2 or parts[1] not in DIRS:
                out("ERROR: usage: move <left|right|forward|backward|up|down>")
                continue
            d = DIRS[parts[1]]
            dest = tuple(s + o for s, o in zip(field.ship, d))
            if not field.in_bounds(dest):
                out("ERROR: that would leave the asteroid field")
                continue
            impacts = field.move(d)
            if impacts:
                if field.hull <= 0:
                    out(f"IMPACT at {field.ship}! Hull breached. The ship breaks apart.")
                    out("GAME OVER")
                    return
                out(f"IMPACT at {field.ship}! Shields absorbed it. Hull: {field.hull}")
            if field.ship == field.goal:
                out("You slip through the jump gate as the asteroid field closes behind you.")
                out(f"Transmission received: {flag}")
                return
            out(f"position {field.ship}")
            continue

        out("ERROR: unknown command. Type 'help'.")


class Handler(socketserver.StreamRequestHandler):
    timeout = TIME_LIMIT + 10

    def handle(self):
        import io
        r = io.TextIOWrapper(self.rfile, encoding="utf-8", errors="replace")
        w = io.TextIOWrapper(self.wfile, encoding="utf-8", write_through=True)
        try:
            run_game(r, w, load_flag())
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class Server(socketserver.ForkingTCPServer if hasattr(os, "fork") else socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--listen":
        port = int(sys.argv[2])
        with Server(("0.0.0.0", port), Handler) as srv:
            print(f"Asteroid Run listening on 0.0.0.0:{port}", flush=True)
            srv.serve_forever()
    else:
        run_game(sys.stdin, sys.stdout, load_flag())


if __name__ == "__main__":
    main()
