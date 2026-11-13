"""
4D Rubik's cube: a 3x3x3x3 tesseract whose 8 cells are each a 3x3x3 cube,
drawn as "rings" the way rubik2d.py draws a 3D cube, one dimension up.

Axes x -> R, y -> B, z -> U as in rubik2d, plus w -> O (outer) / I (inner).
Cubies sit at positions in {-1,0,1}^4 and a sticker is keyed by
(cubie position, outward normal), so there are 8 cells * 27 = 216 stickers.

Rings view. rubik2d gives each of the 3 axes a family of 3 concentric
circles on the corners of a triangle and puts a sticker where the circles of
its two other-axis layers cross. Here each of the 4 axes gets a family of 3
concentric spheres on the corners of a tetrahedron (the 4 axes seen from the
4D corner R-F-U-O), and a sticker sits where the spheres of its three
other-axis layers meet: on the inner side for the 4 near cells (R F U O) and
the outer side for the 4 far ones (L B D I). Turning a layer rolls its
sphere's dots around the sphere, and spins the turning cell's 27 dots
around that cell's centre dot, like rubik2d's rings and face dots.

Debug view (--debug, Tab): the tesseract projected 4D -> 3D (camera out
along +w, so I is the small cell in the middle and O, which would wrap
around everything, is hidden), with cells and stickers shrunk.

Moves are written <cell><direction>: "RU" turns the R cell clockwise as seen
from its U side, i.e. the x=+1 layer rotates in the (y, w) plane. A leading
* turns the whole puzzle, a leading 2 turns the middle layer ("2RU").

Controls (interactive window, needs pygame). The keys are rubik2d's, applied
to the focused cell as if it were a 3D cube, oriented as it looks in the
debug view (for the I cell, exactly the usual R/U/F directions):
    cell buttons (left; colour = the cell's centre)   focus a cell
    1-8           focus R L U D F B O I
    U D L R F B   orbit turns         M E S   central orbit turns
    X Y Z         rotate system: the whole focused cell (a real 4D twist)
    hold Shift for the inverse, Ctrl to turn the whole puzzle instead
    Space         scramble            Backspace  reset
    Mouse drag    orbit the view      Mouse wheel  zoom the view under it
    Tab           show/hide the debug view (only with --debug)
    H             show/hide the O cell in the debug view
    Esc           show/hide the controls screen        Q  quit
    Randomize button (top left) scrambles; a flag appears when solved.

Usage:
    python tesseract2d.py                       # interactive
    python tesseract2d.py "RU FO' *RO 2UF"      # play a sequence, then interactive
    python tesseract2d.py --debug               # also show the 4D debug view
    python tesseract2d.py "RU FO" --gif t.gif   # render a GIF (needs Pillow)
"""

import argparse
import functools
import os
import random
import re

import numpy as np

from rubik2d import (BG, EDGE, INK, MOVES as MOVES3, RING_STYLE, STAR_ALPHA, Sky, button_rect,
                     draw_button, draw_flag, draw_help, draw_hint, draw_star, load_font,
                     rotation, smooth)

# cell letter -> (axis, side)
CELLS = {
    "R": (0, 1), "L": (0, -1),
    "U": (2, 1), "D": (2, -1),
    "F": (1, -1), "B": (1, 1),
    "O": (3, 1), "I": (3, -1),
}
COLORS = {  # rubik2d's scheme for the 3D faces, plus O and I
    (0, 0, 1, 0): (230, 30, 40),      # U red
    (0, 0, -1, 0): (0, 230, 230),     # D cyan
    (0, -1, 0, 0): (20, 200, 40),     # F green
    (0, 1, 0, 0): (20, 40, 230),      # B blue
    (1, 0, 0, 0): (240, 40, 230),     # R magenta
    (-1, 0, 0, 0): (250, 240, 20),    # L yellow
    (0, 0, 0, 1): (255, 140, 20),     # O orange
    (0, 0, 0, -1): (250, 250, 250),   # I white
}

# rings view: sphere radii for the near, middle and far layer, in units of
# the distance from the middle to a sphere family's centre
RADII = (1.5, 1.9, 2.3)
VIEW4 = np.array([1.0, -1.0, 1.0, 1.0]) / 2  # the 4D corner R-F-U-O

# debug view
EYE4 = 5.0             # 4D camera distance along +w
CELL_SHRINK = 0.62     # each cell shrinks toward its centre
STICKER_SHRINK = 0.72  # each sticker shrinks toward its own centre

CAM = 14.0   # 3D camera distance (both views)
FADE = 0.35  # how far cells other than the focused one fade into the background


def normal(cell):
    a, s = CELLS[cell]
    n = [0, 0, 0, 0]
    n[a] = s
    return tuple(n)


def cell_of(n):
    a = int(np.argmax(np.abs(n)))
    return next(c for c, v in CELLS.items() if v == (a, n[a]))


def plane_rotation(i, j, degrees):
    """4x4 rotation in the (i, j) plane taking e_i toward e_j."""
    t = np.radians(degrees)
    c, s = np.cos(t), np.sin(t)
    m = np.eye(4)
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def _twists():
    """'RU' -> (cell axis, cell side, i, j): clockwise is -90 degrees in the
    (i, j) plane, oriented so (cell normal, direction, e_i, e_j) is
    right-handed. That makes every cell but O (which the debug view shows
    inside out) turn clockwise on screen, like a 3D cube."""
    out = {}
    for c, (a, sa) in CELLS.items():
        for d, (b, _) in CELLS.items():
            if a == b:
                continue
            i, j = [k for k in range(4) if k not in (a, b)]
            basis = np.array([normal(c), normal(d), np.eye(4)[i], np.eye(4)[j]])
            if np.linalg.det(basis) < 0:
                i, j = j, i
            out[c + d] = (a, sa, i, j)
    return out


TWISTS = _twists()


def move_info(name):
    """-> (axis, layer, i, j); layer 0 for '2RU', None for '*RU'."""
    a, sa, i, j = TWISTS[name.lstrip("*2")]
    layer = {"*": None, "2": 0}.get(name[0], sa)
    return a, layer, i, j


def move_matrix(name, degrees):
    _, _, i, j = move_info(name)
    return plane_rotation(i, j, degrees)


def parse(seq):
    """"RU FO2 RU' *RO 2UF" -> [(name, quarter_turns)]."""
    out = []
    for tok in seq.replace(",", " ").split():
        m = re.fullmatch(r"([*2]?)([A-Za-z]{2})(2?)(['’]?)(2?)", tok)
        name = m and m.group(1) + m.group(2).upper()
        if not m or name.lstrip("*2") not in TWISTS:
            raise ValueError(f"unknown move: {tok}")
        q = 2 if m.group(3) or m.group(5) else 1
        out.append((name, -q if m.group(4) else q))
    return out


def moving(pos, name):
    axis, layer, _, _ = move_info(name)
    return layer is None or pos[axis] == layer


def cell_frame(cell):
    """3x4 signed permutation: a direction inside `cell` (4D) -> the 3D
    direction it points in the debug view. The O side of a side cell faces
    outward, the I and O cells keep x, y, z."""
    a, s = CELLS[cell]
    p = np.zeros((3, 4), dtype=int)
    for k in range(3):
        if k != a:
            p[k, k] = 1
    if a != 3:
        p[a, 3] = s
    return p


@functools.lru_cache(maxsize=None)
def focus_move(cell, key, whole=False):
    """The 4D move doing rubik2d's `key` (U, M, x, ...) to `cell` as if it
    were a 3D cube; `whole` turns the whole puzzle the same way."""
    a, s = CELLS[cell]
    axis3, layer3, deg3 = MOVES3[key]
    p = cell_frame(cell)
    m4 = p.T @ np.rint(rotation(axis3, deg3)).astype(int) @ p
    m4[a, a] = 1
    if layer3 is None:  # x y z: the cell's own layer
        axis, layer = a, s
    else:
        axis = int(np.flatnonzero(p[axis3])[0])
        layer = layer3 * p[axis3, axis]
    for name, (ta, tsa, i, j) in TWISTS.items():
        if ta == axis and tsa == (layer or 1) and \
                np.array_equal(np.rint(plane_rotation(i, j, -90)), m4):
            return ("*" if whole else "2" if layer == 0 else "") + name
    raise AssertionError((cell, key))


# ----------------------------------------------------------------- state
# Each cell is also a regular Rubik's cube: a sticker is a little cubie whose
# sides facing out of its cell's 3x3x3 get the usual face colours, by the
# direction they face in the cell (as the focus keys see it: cell_frame).
FACE_COLOURS = {
    "U": (245, 245, 245),  # white
    "D": (255, 214, 0),    # yellow
    "F": (0, 185, 75),     # green
    "B": (25, 90, 235),    # blue
    "R": (225, 30, 45),    # red
    "L": (255, 125, 0),    # orange
}
LOCAL_FACE = {(1, 0, 0): "R", (-1, 0, 0): "L", (0, 1, 0): "B", (0, -1, 0): "F",
              (0, 0, 1): "U", (0, 0, -1): "D"}


@functools.lru_cache(maxsize=None)
def local_face(cell, d):
    """Which face (U, R, ...) of `cell`'s cube the 4D direction d points at."""
    return LOCAL_FACE[tuple(int(v) for v in cell_frame(cell) @ d)]


class Tesseract:
    """Stickers keyed by location (cubie position in {-1,0,1}^4, outward
    normal) -> (home cell, facets): the cell the sticker belongs to, and its
    coloured sides as ((4D direction it faces now, colour), ...)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.stickers = {}
        for p in np.ndindex(3, 3, 3, 3):
            pos = tuple(v - 1 for v in p)
            for a in range(4):
                if pos[a]:
                    n = [0, 0, 0, 0]
                    n[a] = pos[a]
                    cell = cell_of(n)
                    facets = []
                    for k in range(4):
                        if k != a and pos[k]:
                            d = tuple(pos[k] * int(x == k) for x in range(4))
                            facets.append((d, FACE_COLOURS[local_face(cell, d)]))
                    self.stickers[(pos, tuple(n))] = (cell, tuple(facets))

    def apply(self, name, quarter_turns=1):
        m = np.rint(move_matrix(name, -90 * quarter_turns)).astype(int)
        turn = lambda v: tuple(int(x) for x in m @ v)
        new = {}
        for (pos, n), (home, facets) in self.stickers.items():
            if moving(pos, name):
                pos, n = turn(pos), turn(n)
                facets = tuple((turn(d), c) for d, c in facets)
            new[(pos, n)] = (home, facets)
        self.stickers = new

    def home(self, key):
        return self.stickers[key][0]

    def colour(self, key):
        """The sticker's cell colour (one per cell: tesseract2d's look)."""
        return COLORS[normal(self.stickers[key][0])]

    def facets(self, key):
        """{4D direction: colour} of the sticker's coloured sides."""
        return dict(self.stickers[key][1])

    def centre(self, cell):
        """Home cell of a cell's centre sticker (only slices and whole-puzzle
        turns move it, as on a 3D cube)."""
        n = normal(cell)
        return self.stickers[(n, n)][0]

    def solved(self, faces=True):
        """Every cell holds stickers of one home cell, and (with `faces`)
        every face of every cell's cube is one colour, like a solved Rubik's
        cube. Whole-puzzle turns don't matter."""
        homes, colours = {}, {}
        for (pos, n), (home, facets) in self.stickers.items():
            homes.setdefault(n, set()).add(home)
            for d, c in facets:
                colours.setdefault((n, d), set()).add(c)
        if any(len(h) > 1 for h in homes.values()):
            return False
        return not faces or all(len(c) == 1 for c in colours.values())


def state_key(tess):
    """SHA-256 of the tesseract's full state (every sticker's home cell and
    coloured sides), after turning the whole puzzle so each cell's centre
    sits where it does in a fresh tesseract: a solved tesseract gives the same
    key in any orientation, any other state a different one. (The flag is
    sealed with it; see tesseract3d.reveal_flag and seal_flag.py.)"""
    import hashlib
    # the whole-puzzle turn the centres show: column k is where the centre of
    # the cell on +axis k is now (centres only ever move together, rigidly)
    turn = np.zeros((4, 4), dtype=int)
    for a in range(4):
        home = cell_of(tuple(int(x == a) for x in range(4)))
        where = [n for (pos, n), (h, _) in tess.stickers.items() if pos == n and h == home]
        turn[:, a] = where[0]
    back = lambda v: tuple(int(x) for x in turn.T @ v)  # undo it
    state = sorted((back(pos), back(n), home, tuple(sorted((back(d), c) for d, c in facets)))
                   for (pos, n), (home, facets) in tess.stickers.items())
    return hashlib.sha256(repr(state).encode()).digest()


KEYS = list(Tesseract().stickers)  # every sticker location, fixed order


# ----------------------------------------------------------------- rings geometry
# Centre of each axis's sphere family (toward that axis's near cell): the
# corners of a regular tetrahedron, seen down a 2-fold axis from -y as a
# diamond with F left, R right (the near edge, as in rubik2d's corner view),
# U on top and O at the bottom.
CENTRES = [np.array(v) / np.sqrt(1.5) for v in (
    (1.0, -np.sqrt(0.5), 0.0),    # x: R
    (-1.0, -np.sqrt(0.5), 0.0),   # y: F
    (0.0, np.sqrt(0.5), 1.0),     # z: U
    (0.0, np.sqrt(0.5), -1.0),    # w: O
)]


def sphere_radius(axis, layer):
    """Radius of the sphere holding the stickers in that layer."""
    return RADII[1 - layer * int(np.sign(VIEW4[axis]))]


@functools.lru_cache(maxsize=None)
def sticker_xyz(pos, n):
    """Where a sticker's dot sits in the rings view: where the spheres of its
    three other-axis layers meet."""
    a = int(np.argmax(np.abs(n)))
    b, c, d = [k for k in range(4) if k != a]
    p1, p2, p3 = CENTRES[b], CENTRES[c], CENTRES[d]
    r1, r2, r3 = (sphere_radius(k, pos[k]) for k in (b, c, d))
    dist = np.linalg.norm(p2 - p1)
    ex = (p2 - p1) / dist
    i = ex @ (p3 - p1)
    ey = p3 - p1 - i * ex
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    j = ey @ (p3 - p1)
    x = (r1 * r1 - r2 * r2 + dist * dist) / (2 * dist)
    y = (r1 * r1 - r3 * r3 + i * i + j * j) / (2 * j) - i * x / j
    base = p1 + x * ex + y * ey
    h = np.sqrt(max(0.0, r1 * r1 - x * x - y * y))
    side = np.sign((CENTRES[a] - base) @ ez)  # inner side, toward CENTRES[a]
    if n[a] * VIEW4[a] < 0:  # far cell: outer side
        side = -side
    return base + side * h * ez


def turn_xyz(q0, q1, qq, pivot, axis, s):
    """Move a dot from q0 to q1 around the line through `pivot` along `axis`
    (fraction s of the turn), going the way a quarter turn takes it (to qq).
    The distance to the pivot is kept, so sphere dots roll on their sphere."""
    if np.linalg.norm(q1 - q0) < 1e-9:
        return q0
    u = axis / np.linalg.norm(axis)
    v0, v1, vq = q0 - pivot, q1 - pivot, qq - pivot
    h0, h1 = v0 @ u, v1 @ u
    p0, p1, pq = v0 - h0 * u, v1 - h1 * u, vq - (vq @ u) * u
    r0, r1 = np.linalg.norm(p0), np.linalg.norm(p1)
    if r0 < 1e-6 or r1 < 1e-6:
        return q0 + (q1 - q0) * s
    e1 = p0 / r0
    e2 = np.cross(u, e1)
    f1 = np.arctan2(p1 @ e2, p1 @ e1)
    sense = 1 if np.arctan2(pq @ e2, pq @ e1) >= 0 else -1
    f = sense * ((sense * f1) % (2 * np.pi)) * s
    v = (h0 + (h1 - h0) * s) * u + (r0 + (r1 - r0) * s) * (np.cos(f) * e1 + np.sin(f) * e2)
    d = np.linalg.norm(v0) + (np.linalg.norm(v1) - np.linalg.norm(v0)) * s
    return pivot + v * d / np.linalg.norm(v)


def ring_pivot(pos, n, name):
    """(pivot, axis) a moving dot turns around: a turning cell's dots spin
    around its centre dot, every other dot rolls around its sphere's centre,
    toward the pole held still by the turn."""
    a, _, i, j = move_info(name)
    k = next(x for x in range(4) if x not in (a, i, j))
    ek = tuple(int(x == k) for x in range(4))
    if n[a]:
        pivot = sticker_xyz(n, n)
        return pivot, sticker_xyz(tuple(np.add(n, ek)), n) - pivot
    pole = tuple(pos[a] * (x == a) + (x == k) for x in range(4))
    return CENTRES[a], sticker_xyz(pole, ek) - CENTRES[a]


# ----------------------------------------------------------------- debug geometry
def _sticker_verts(pos, n):
    """8 corners (4D) of a sticker: a small cube inside its cell's hyperplane,
    shrunk toward the cell centre and then toward its own centre."""
    a = int(np.argmax(np.abs(n)))
    rest = [k for k in range(4) if k != a]
    cell_c = 1.5 * np.array(n, dtype=float)
    c = cell_c + CELL_SHRINK * (np.array(pos) + 0.5 * np.array(n) - cell_c)
    h = 0.5 * CELL_SHRINK * STICKER_SHRINK
    out = []
    for bits in np.ndindex(2, 2, 2):
        v = c.copy()
        for k, b in zip(rest, bits):
            v[k] += h if b else -h
        out.append(v)
    return out


VERTS = np.array([_sticker_verts(p, n) for p, n in KEYS])  # (216, 8, 4)
# the 6 faces of a sticker cube, as cycles of corner indices
FACES = np.array([
    [0, 2, 3, 1], [4, 6, 7, 5],
    [0, 1, 5, 4], [2, 3, 7, 6],
    [0, 4, 6, 2], [1, 5, 7, 3],
])


def project4(v):
    """4D -> 3D perspective, camera at w = EYE4."""
    return v[..., :3] * (EYE4 / (EYE4 - v[..., 3:]))


# ----------------------------------------------------------------- drawing
class Camera:
    """An orbiting perspective camera looking at the origin, drawing into
    `rect`; z is up."""

    def __init__(self, rect, extent, view=(1.0, -1.5, 1.15)):
        v = np.array(view, dtype=float)
        self.yaw = np.arctan2(v[1], v[0])
        self.pitch = np.arcsin(v[2] / np.linalg.norm(v))
        self.extent = extent
        self.place(rect)

    def place(self, rect):
        self.rect = rect
        self.scale = min(rect.w, rect.h) * 0.47 / self.extent

    def orbit(self, dx, dy):
        self.yaw -= dx * 0.008
        self.pitch = float(np.clip(self.pitch + dy * 0.008, -1.45, 1.45))

    def zoom(self, factor):
        lo = min(self.rect.w, self.rect.h) * 0.05 / self.extent
        self.scale = float(np.clip(self.scale * factor, lo, lo * 200))

    def axes(self):
        cp = np.cos(self.pitch)
        view = np.array([cp * np.cos(self.yaw), cp * np.sin(self.yaw), np.sin(self.pitch)])
        up = np.array([0.0, 0.0, 1.0]) - view[2] * view
        up /= np.linalg.norm(up)
        return view, up, np.cross(up, view)

    def project(self, p):
        """-> screen xy (..., 2), depth toward the viewer, perspective factor."""
        view, up, right = self.axes()
        depth = p @ view
        k = self.scale * CAM / (CAM - depth)
        xy = np.stack([self.rect.centerx + (p @ right) * k,
                       self.rect.centery - (p @ up) * k], axis=-1)
        return xy, depth, k


def fade(col, amount):
    return tuple(int(c * (1 - amount) + b * amount) for c, b in zip(col, BG))


class Scene:
    def __init__(self, width=1200, height=600, show3d=True, panel=0):
        import pygame
        import pygame.gfxdraw
        self.pg = pygame
        self.w, self.h, self.panel = width, height, panel
        self.surface = pygame.Surface((width, height))
        self.focus = "I"
        self.show_outer = False
        r = np.linalg.norm(project4(VERTS[[n[3] < 1 for _, n in KEYS]]), axis=-1).max()
        self.rings = Camera(pygame.Rect(0, 0, 1, 1), 1 + RADII[2], view=(0.3, -1.0, 0.35))
        self.debug = Camera(pygame.Rect(0, 0, 1, 1), r)
        pts = np.array([sticker_xyz(p, n) for p, n in KEYS])
        d = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(len(pts)) * 1e9
        self.dot = 0.31 * d.min()  # dot radius, rings-view units
        self.show3d = show3d
        self.sky = Sky(width, height)
        self.time = 0.0  # seconds, for the sky's animation
        self.layout()

    def layout(self):
        """Rings view right of the button panel (left half with the debug view
        on, whole window otherwise), debug view in the right half."""
        rect = self.pg.Rect
        split = self.w // 2 if self.show3d else self.w
        self.rings.place(rect(self.panel, 0, split - self.panel, self.h))
        self.debug.place(rect(split, 0, self.w - split, self.h))

    def toggle_3d(self):
        self.show3d = not self.show3d
        self.layout()

    def camera_at(self, xy):
        if self.show3d and self.debug.rect.collidepoint(xy):
            return self.debug
        return self.rings

    def _circle(self, col, centre, r, width=1):
        """Antialiased circle outline (or a filled disc when width is 0)."""
        gfx, s = self.pg.gfxdraw, self.surface
        x, y = int(round(centre[0])), int(round(centre[1]))
        if width == 0:
            gfx.filled_circle(s, x, y, r, col)
            gfx.aacircle(s, x, y, r, col)
            return
        if width > 1:
            self.pg.draw.circle(s, col, (x, y), r + width // 2, width)
        for k in range(width):
            gfx.aacircle(s, x, y, r + width // 2 - k, col)

    def draw(self, tess, move=None, angle=0.0, total=None):
        self.sky.draw(self.surface, self.time)
        self._draw_rings(tess, move, angle, total)
        if self.show3d:
            self._draw_debug(tess, move, angle, total)
            self.pg.draw.line(self.surface, RING_STYLE[1][0], self.debug.rect.topleft,
                              self.debug.rect.bottomleft, 2)
        self.surface.set_clip(None)
        return self.surface

    def _draw_rings(self, tess, move, angle, total):
        cam = self.rings
        self.surface.set_clip(cam.rect)
        lim = 4 * max(self.w, self.h)

        # spheres, drawn as their outlines (middle layer faint, as in rubik2d)
        for a in range(4):
            xy, _, k = cam.project(CENTRES[a])
            for r, (col, width) in zip(RADII, RING_STYLE):
                if np.all(np.abs(xy) < lim) and r * k < lim:
                    self._circle(col, xy, int(round(r * k)), width)

        dots = []
        if move:
            snap = np.rint(move_matrix(move, total)).astype(int)
            quarter = np.rint(move_matrix(move, 90 * np.sign(total))).astype(int)
        focus = normal(self.focus)
        for pos, n in tess.stickers:
            col = tess.colour((pos, n))
            q = sticker_xyz(pos, n)
            if move and moving(pos, move):
                q1 = sticker_xyz(tuple(snap @ pos), tuple(snap @ n))
                qq = sticker_xyz(tuple(quarter @ pos), tuple(quarter @ n))
                q = turn_xyz(q, q1, qq, *ring_pivot(pos, n, move), angle / total)
            dots.append((q, col, 1.0 if n == focus else 1 - FADE))
        xy, depth, k = cam.project(np.array([q for q, _, _ in dots]))
        for i in np.argsort(depth):  # far dots first
            x, y = xy[i]
            if abs(x) < lim and abs(y) < lim:
                draw_star(self.surface, dots[i][1], (x, y), self.dot * k[i], dots[i][2])

    def _draw_debug(self, tess, move, angle, total):
        pg, s, cam = self.pg, self.surface, self.debug
        s.set_clip(cam.rect)
        view, up, right = cam.axes()
        eye = view * CAM

        # where each sticker is (4D), with the moving layer part-way round
        verts = VERTS.copy()
        hide = np.array([n == normal("O") for _, n in KEYS])
        if move:
            busy = np.array([moving(p, move) for p, _ in KEYS])
            verts[busy] = verts[busy] @ move_matrix(move, angle).T
            snap = np.rint(move_matrix(move, total)).astype(int)
            ends = np.array([tuple(snap @ n) == normal("O") if b else h
                             for (_, n), b, h in zip(KEYS, busy, hide)])
            hide &= ends  # show stickers on their way in or out of O
        if self.show_outer or self.focus == "O":
            hide[:] = False

        p3 = project4(verts)                         # (216, 8, 3)
        quads = p3[:, FACES]                         # (216, 6, 4, 3)
        fc = quads.mean(axis=2)
        nrm = np.cross(quads[:, :, 1] - quads[:, :, 0], quads[:, :, 3] - quads[:, :, 0])
        out = np.einsum("sfk,sfk->sf", nrm, fc - p3.mean(axis=1)[:, None])
        nrm *= np.where(out < 0, -1.0, 1.0)[..., None]
        visible = np.einsum("sfk,sfk->sf", nrm, eye - fc) > 0
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-12
        light = view + 0.6 * up - 0.3 * right
        shade = 0.55 + 0.45 * np.clip(nrm @ (light / np.linalg.norm(light)), 0, 1)
        screen, _, _ = cam.project(p3)               # (216, 8, 2)

        focus = normal(self.focus)
        dist = np.linalg.norm(p3.mean(axis=1) - eye, axis=1)
        for si in np.argsort(-dist):                 # far stickers first
            if hide[si]:
                continue
            col = np.array(tess.colour(KEYS[si]), dtype=float)
            dim = KEYS[si][1] != focus
            alpha = int(255 * STAR_ALPHA * (1 - FADE if dim else 1)) + 60
            outline = INK + ((90 if dim else 220),)
            for f in np.flatnonzero(visible[si]):  # translucent, white outline
                c = tuple((col * shade[si, f]).astype(int)) + (alpha,)
                pts = [tuple(p) for p in np.rint(screen[si, FACES[f]]).astype(int)]
                pg.gfxdraw.filled_polygon(s, pts, c)
                pg.gfxdraw.aapolygon(s, pts, outline)


def animate(scene, tess, name, q, steps):
    """Yield surfaces animating one move, then apply it."""
    total = -90 * q
    n = steps * abs(q)
    for k in range(1, n):
        yield scene.draw(tess, name, total * smooth(k / n), total)
    tess.apply(name, q)
    yield scene.draw(tess)


def scramble(length=30, rng=random):
    seq, last = [], None
    for _ in range(length):
        cell = rng.choice([c for c in CELLS if c != last])
        d = rng.choice([d for d in CELLS if CELLS[d][0] != CELLS[cell][0]])
        seq.append((cell + d, rng.choice([1, -1, 2])))
        last = cell
    return seq


# ----------------------------------------------------------------- outputs
def save_gif(seq, path, width=640, steps=12, debug=False):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from PIL import Image

    pygame.init()
    scene = Scene(width, width // 2 if debug else width * 3 // 4, show3d=debug)
    tess = Tesseract()

    def grab(surf):
        return Image.fromarray(pygame.surfarray.array3d(surf).transpose(1, 0, 2))

    frames = []

    def still(count):
        for _ in range(count):
            scene.time = len(frames) / 30
            frames.append(grab(scene.draw(tess)))

    still(10)
    for name, q in seq:
        for f in animate(scene, tess, name, q, steps):
            frames.append(grab(f))
            scene.time = len(frames) / 30
        still(3)
    still(15)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0)
    print(f"saved {path} ({len(frames)} frames)")


def focus_buttons(pygame, top, pad, size):
    """Cell letter -> Rect: the 8 cells in pairs (R L / U D / F B / O I)."""
    out = {}
    for k, cell in enumerate(CELLS):
        out[cell] = pygame.Rect(pad + (k % 2) * (size + pad), top + (k // 2) * (size + pad),
                                size, size)
    return out


def draw_focus_button(screen, rect, cell, col, font, focused, hover):
    """A swatch of the cell's centre colour; the focused one is ringed."""
    import pygame
    if focused:
        pygame.draw.rect(screen, INK, rect.inflate(10, 10), 3, border_radius=10)
    pygame.draw.rect(screen, col if focused or hover else fade(col, 0.15), rect, border_radius=7)
    pygame.draw.rect(screen, EDGE, rect, 2, border_radius=7)
    if font:
        text = font.render(cell, True, EDGE)
        screen.blit(text, text.get_rect(center=rect.center))


def help_rows(debug, three_d=False, solve=True):
    """(keys, action) rows for the controls screen (tesseract3d adds
    click-to-focus and the lattice toggle; solve=False leaves out Space)."""
    if three_d:  # cells are galaxies of shapes there, each a Rubik's cube
        rows = [("Focus", None),
                ("Galaxy buttons, 1-8", "focus a galaxy (hover for its name)"),
                ("Click a shape", "focus its galaxy"),
                ("Ctrl + click", "show only that galaxy, centred (again: all)")]
    else:
        rows = [("Focus", None),
                ("Cell buttons, 1-8", "focus a cell: R L U D F B O I")]
    rows += [("Turns (on the focused cell)", None),
             ("U D L R F B", "orbit turns"),
             ("M E S", "central orbit turns"),
             ("X Y Z", "rotate system (the whole focused cell)"),
             ("Shift + key", "inverse"),
             ("Ctrl + key", "turn the whole puzzle instead")]
    if not three_d:  # (tesseract3d starts scrambled; Space solves, with --debug)
        rows += [("Puzzle", None),
                 ("Space", "scramble (or the Randomize button)"),
                 ("Backspace", "reset")]
    rows += [("View", None),
             ("Mouse drag", "orbit the view"),
             ("Mouse wheel", "zoom the view under the mouse")]
    if three_d:
        rows.append(("G", "lattice on every cell"))
    if debug:
        rows += [("Tab", "show/hide the debug view"),
                 ("H", "show/hide the O cell (debug view)")]
        if three_d and solve:
            rows.append(("Space", "solve (debug only)"))
    return rows + [("Esc", "show/hide this screen"), ("Q", "quit")]


def run_window(initial=(), width=1200, debug=False):
    import pygame

    pygame.init()
    height = width // 2
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("RASA Calibration Panel")
    clock = pygame.time.Clock()
    font = load_font(max(16, height // 20))
    small = load_font(max(14, height // 30))
    pad = height // 40
    button = button_rect(pad, height, font)
    size = height // 11
    cells = focus_buttons(pygame, button.bottom + 3 * pad, pad, size)
    panel = max(button.right, max(r.right for r in cells.values())) + pad
    scene, tess = Scene(width, height, show3d=debug, panel=panel), Tesseract()
    queue, anim = list(initial), None
    keymap = {getattr(pygame, f"K_{k.lower()}"): k for k in MOVES3}
    numbers = {getattr(pygame, f"K_{k + 1}"): c for k, c in enumerate(CELLS)}
    dragging, show_help = None, False

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    running = False
                elif ev.key == pygame.K_ESCAPE:
                    show_help = not show_help
                elif show_help:
                    pass  # the controls screen takes no other keys
                elif ev.key == pygame.K_SPACE:
                    queue += scramble()
                elif ev.key == pygame.K_TAB and debug:
                    scene.toggle_3d()
                elif ev.key == pygame.K_BACKSPACE:
                    queue, anim = [], None
                    tess.reset()
                elif ev.key == pygame.K_h:
                    scene.show_outer = not scene.show_outer
                elif ev.key in numbers:
                    scene.focus = numbers[ev.key]
                elif ev.key in keymap:
                    name = focus_move(scene.focus, keymap[ev.key],
                                      bool(ev.mod & pygame.KMOD_CTRL))
                    queue.append((name, -1 if ev.mod & pygame.KMOD_SHIFT else 1))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                hit = [c for c, r in cells.items() if r.collidepoint(ev.pos)]
                if show_help:
                    show_help = False
                elif button.collidepoint(ev.pos):
                    queue += scramble()
                elif hit:
                    scene.focus = hit[0]
                else:
                    dragging = scene.camera_at(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                dragging = None
            elif ev.type == pygame.MOUSEMOTION and dragging:
                dragging.orbit(*ev.rel)
            elif ev.type == pygame.MOUSEWHEEL and not show_help:
                scene.camera_at(pygame.mouse.get_pos()).zoom(1.1 ** ev.y)

        scene.time = pygame.time.get_ticks() / 1000
        if anim is None and queue:
            name, q = queue.pop(0)
            anim = animate(scene, tess, name, q, 5 if len(queue) > 3 else 16)
        if anim is not None:
            try:
                frame = next(anim)
            except StopIteration:
                anim = None
        if anim is None:  # redraw every frame: the sky is animated
            frame = scene.draw(tess)

        screen.blit(frame, (0, 0))
        mouse = pygame.mouse.get_pos()
        draw_button(screen, button, "Randomize", font, button.collidepoint(mouse))
        for cell, rect in cells.items():
            draw_focus_button(screen, rect, cell, COLORS[normal(tess.centre(cell))], font,
                              cell == scene.focus, rect.collidepoint(mouse))
        if anim is None and not queue and tess.solved(faces=False):  # (faces aren't shown here)
            size = height // 8
            draw_flag(screen, width - pad - size, pad + 4, size, font)
        if show_help:
            draw_help(screen, help_rows(debug), max(14, height // 30))
        else:
            draw_hint(screen, small)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RASA calibration panel")
    ap.add_argument("moves", nargs="?", default="", help="e.g. \"RU FO' *RO 2UF\"")
    ap.add_argument("--gif", help="write an animated GIF instead of opening a window")
    ap.add_argument("--width", type=int, default=None)
    # --debug (debug view, Tab, Space-solve) works but is left out of --help
    ap.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    seq = parse(args.moves)
    if args.gif:
        save_gif(seq or scramble(12), args.gif, width=args.width or 640, debug=args.debug)
    else:
        run_window(seq, width=args.width or 1200, debug=args.debug)
