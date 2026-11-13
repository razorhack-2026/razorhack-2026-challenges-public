#!/usr/bin/env python3
"""
Reference solver for BLIND PILOT.

Strategy
  * Every tick, scan all 26 neighbours and record each asteroid's position and
    velocity.
  * Remember every asteroid ever seen and propagate it forward each tick
    (motion is deterministic, bouncing off the edges), so the map of "known" rocks grows.
  * Pick the next move with a short space-time search: simulate the known
    rocks a few ticks ahead, score each move sequence by impacts, by the risk of
    unknown cells, and by distance to the jump gate, then play the first move.

Usage:
    python3 solve.py HOST PORT
"""
import itertools
import re
import socket
import sys

DIRS = {
    "right": (1, 0, 0), "left": (-1, 0, 0),
    "forward": (0, 1, 0), "backward": (0, -1, 0),
    "up": (0, 0, 1), "down": (0, 0, -1),
}
NAME_TO_VEL = DIRS
def neighbours(r):
    rng = range(-r, r + 1)
    return [d for d in itertools.product(rng, repeat=3) if d != (0, 0, 0)]


NEIGHBOURS = neighbours(1)

DEPTH = 3            # ticks of lookahead
IMPACT_COST = 1000
UNKNOWN_COST = 3     # rough penalty for a cell whose arrivals we can't predict


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def drift(pos, v, n):
    """Asteroids bounce: off the edge, the direction reverses."""
    nxt = add(pos, v)
    if not all(0 <= c < n for c in nxt):
        v = (-v[0], -v[1], -v[2])
        nxt = add(pos, v)
    return nxt, v


class Pilot:
    def __init__(self, n, ship, goal):
        self.n = n
        self.ship = ship
        self.goal = goal
        self.known = {}      # (x,y,z) -> list of velocities, believed current
        self.seen = {ship}   # cells whose contents we know right now

    # ---- knowledge bookkeeping -------------------------------------------
    def in_bounds(self, p):
        return all(0 <= c < self.n for c in p)

    def record_scan(self, cell, vels):
        """Overwrite our belief about one cell with fresh sensor data."""
        if vels:
            self.known[cell] = list(vels)
        else:
            self.known.pop(cell, None)
        self.seen.add(cell)

    def advance(self, d):
        """The ship moved by d and every asteroid drifted one cell."""
        self.ship = add(self.ship, d)
        self.known = self.future(self.known, 1)
        # fresh scans come next tick; our own cell is the only one we know is clear
        self.seen = {self.ship}

    # ---- planning ----------------------------------------------------------
    def future(self, known, steps):
        out = known
        for _ in range(steps):
            nxt = {}
            for p, vels in out.items():
                for v in vels:
                    q, w = drift(p, v, self.n)
                    nxt.setdefault(q, []).append(w)
            out = nxt
        return out

    def plan(self):
        states = [self.known]
        for _ in range(DEPTH):
            states.append(self.future(states[-1], 1))

        best = None
        for seq in itertools.product(DIRS.items(), repeat=DEPTH):
            pos = self.ship
            cost = 0
            ok = True
            steps = 0
            for t, (_, d) in enumerate(seq):
                steps = t + 1
                nxt = add(pos, d)
                if not self.in_bounds(nxt):
                    ok = False
                    break
                if nxt in states[t]:                 # fly into a known rock
                    cost += IMPACT_COST * len(states[t][nxt])
                if nxt in states[t + 1]:             # known rock drifts onto us
                    cost += IMPACT_COST * len(states[t + 1][nxt])
                if t == 0:
                    # any rock arriving next tick comes from a face-adjacent
                    # cell; penalise the ones we have no data on (with the
                    # default radar that is the cell two steps ahead)
                    for v in DIRS.values():
                        src = add(nxt, v)
                        if self.in_bounds(src) and src not in self.seen and src not in states[0]:
                            cost += UNKNOWN_COST
                pos = nxt
                if pos == self.goal:
                    break
            if not ok:
                continue
            dist = sum(abs(a - b) for a, b in zip(pos, self.goal))
            score = cost + dist * 10
            if pos == self.goal:
                score -= 500 - 100 * steps   # reach the gate, and sooner is better
            if best is None or score < best[0]:
                best = (score, seq[0][0], seq[0][1])
        return best[1], best[2]


# ---------------------------------------------------------------- networking
class Conn:
    def __init__(self, host, port):
        self.s = socket.create_connection((host, port))
        self.buf = b""

    def recv_until(self, token=b"> "):
        while token not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                data, self.buf = self.buf, b""
                return data.decode()
            self.buf += chunk
        i = self.buf.index(token) + len(token)
        data, self.buf = self.buf[:i], self.buf[i:]
        return data.decode()

    def send(self, line):
        self.s.sendall(line.encode() + b"\n")


def parse_scan(line):
    # "(1,0,-1) asteroid moving left moving up" | "(1,0,-1) empty" | "... out of bounds"
    if "asteroid" not in line:
        return []
    return [NAME_TO_VEL[w] for w in re.findall(r"moving (\w+)", line)]


def main():
    host, port = sys.argv[1], int(sys.argv[2])
    c = Conn(host, port)
    intro = c.recv_until()
    print(intro)
    m = re.search(r"is (\d+)x", intro)
    n = int(m.group(1))
    ship = tuple(map(int, re.search(r"Ship position: \((\d+), (\d+), (\d+)\)", intro).groups()))
    goal = tuple(map(int, re.search(r"Jump gate: \((\d+), (\d+), (\d+)\)", intro).groups()))
    pilot = Pilot(n, ship, goal)
    radar = neighbours(int(re.search(r"Radar range: (\d+)", intro).group(1)))

    while True:
        # batch all 26 scans in one send to save round trips
        cells = [(d, add(pilot.ship, d)) for d in radar]
        cells = [(d, p) for d, p in cells if pilot.in_bounds(p)]
        c.send("\n".join(f"scan {d[0]},{d[1]},{d[2]}" for d, _ in cells))
        for d, p in cells:
            pilot.record_scan(p, parse_scan(c.recv_until().splitlines()[0]))

        name, d = pilot.plan()
        c.send(f"move {name}")
        reply = c.recv_until()
        pilot.advance(d)
        if "IMPACT" in reply or "Transmission" in reply or "GAME OVER" in reply:
            print(reply.strip())
        if "Transmission" in reply or "GAME OVER" in reply or "FAILURE" in reply:
            break


if __name__ == "__main__":
    main()
