"""
2D "circles" representation of a Rubik's cube, next to an animated 3D cube.

Each of the 54 stickers becomes a dot. A 3x3 cube has 9 rings of 12
stickers (3 layers along each of the 3 axes) and every sticker sits on
exactly two of them. In the picture each axis owns a family of 3 concentric
circles (one per layer), centred on the corners of an equilateral triangle,
so the dots are placed where:

    sticker on cubie (i, j, k) with outward normal along axis a
    -> the crossing of the circles of its two other-axis layers,
       on the inner side for the 3 faces nearest the viewer
       and on the outer side for the 3 far faces

Turning a layer slides its ring dots along their circle and spins the
face dots around the face's centre dot.

Controls (interactive window, needs pygame):
    U D L R F B   orbit turns         M E S   central orbit turns
    X Y Z         rotate system       hold Shift for the inverse (U')
    Space         solve (only with --debug)
    Mouse wheel   zoom the 2D view    Tab  show/hide the 3D cube (--debug)
    Esc           show/hide the controls screen        Q  quit
    The cube starts scrambled; solving it shows the flag. A start screen
    (assets/cube_solved.png, remade if missing) shows the solved circles
    until any key or click.

Usage:
    python rubik2d.py                          # interactive, starts scrambled
    python rubik2d.py "R U R' U'"               # scrambled, then play a sequence
    python rubik2d.py --debug                  # also show the 3D cube
    python rubik2d.py "R U R' U'" --gif a.gif  # render a GIF (needs Pillow)

Requires numpy and pygame (plus Pillow for --gif).
"""

import argparse
import functools
import hashlib
import os
import random

import numpy as np

# Axes: x -> R, y -> B, z -> U  (right-handed, so F is -y and D is -z).
# Radii of each axis's 3 concentric circles, for the layer nearest the
# viewer, the middle layer and the farthest layer, in units of the distance
# from the picture centre to a circle family's centre.
RADII = (1.10, 1.435, 1.765)

COLORS = {  # face normal -> RGB (the bright scheme from the gif)
    (0, 0, 1): (230, 30, 40),     # U red
    (0, 0, -1): (0, 230, 230),    # D cyan
    (0, -1, 0): (20, 200, 40),    # F green
    (0, 1, 0): (20, 40, 230),     # B blue
    (1, 0, 0): (240, 40, 230),    # R magenta
    (-1, 0, 0): (250, 240, 20),   # L yellow
}
EDGE = (25, 25, 25)

# space theme: a near-black backdrop full of stars, light lines on top
SKY_TOP, SKY_BOTTOM = (1, 1, 5), (7, 8, 20)
BG = (4, 4, 12)        # the sky's average colour, for things that fade into it
INK = (232, 236, 250)  # light foreground (rings, flag) on the sky
RING_STYLE = (INK, 2), ((112, 122, 165), 2), (INK, 4)  # near/mid/far
STAR_ALPHA = 0.55  # opacity of a sticker's coloured body (lower = more see-through)

# move -> (axis, layer, angle in degrees about the +axis direction)
# Clockwise as seen from outside a face = -90 degrees about its outward normal.
MOVES = {
    "U": (2, 1, -90), "D": (2, -1, 90),
    "R": (0, 1, -90), "L": (0, -1, 90),
    "B": (1, 1, -90), "F": (1, -1, 90),
    "M": (0, 0, 90),  "E": (2, 0, 90), "S": (1, 0, -90),
    "x": (0, None, -90), "y": (2, None, -90), "z": (1, None, 90),
}  # layer: +1 / -1 outer layers, 0 middle slice, None whole cube

# camera: looking at the U-F-R corner, U up
VIEW = np.array([1.0, -1.0, 1.0]) / np.sqrt(3)       # towards the viewer
UP = np.array([0.0, 0.0, 1.0]) - VIEW / np.sqrt(3)
UP /= np.linalg.norm(UP)
RIGHT = np.cross(UP, VIEW)

# the 3D cube gets its own, slightly off-corner perspective camera
_v = np.array([1.0, -1.5, 1.15])
VIEW3 = _v / np.linalg.norm(_v)
UP3 = np.array([0.0, 0.0, 1.0]) - VIEW3[2] * VIEW3
UP3 /= np.linalg.norm(UP3)
RIGHT3 = np.cross(UP3, VIEW3)
EYE3 = VIEW3 * 10.0


def rotation(axis, degrees):
    t = np.radians(degrees)
    c, s = np.cos(t), np.sin(t)
    i, j = [(1, 2), (2, 0), (0, 1)][axis]
    m = np.eye(3)
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def parse(seq):
    """'R U2 R\\' x' -> [(name, quarter_turns)], quarter_turns in {1, 2, -1, -2}."""
    out = []
    for tok in seq.replace(",", " ").split():
        name = tok[0] if tok[0] in "xyz" else tok[0].upper()
        if name not in MOVES:
            raise ValueError(f"unknown move: {tok}")
        q = 2 if "2" in tok else 1
        if "'" in tok or "’" in tok:
            q = -q
        out.append((name, q))
    return out


def moving(pos, name):
    axis, layer, _ = MOVES[name]
    return layer is None or pos[axis] == layer


# ----------------------------------------------------------------- cube state
class Cube:
    """Stickers keyed by (cubie position in {-1,0,1}^3, outward normal)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.stickers = {}
        for p in np.ndindex(3, 3, 3):
            pos = tuple(v - 1 for v in p)
            for a in range(3):
                if pos[a]:
                    n = [0, 0, 0]
                    n[a] = pos[a]
                    self.stickers[(pos, tuple(n))] = COLORS[tuple(n)]

    def apply(self, name, quarter_turns=1):
        axis, _, deg = MOVES[name]
        m = np.rint(rotation(axis, deg * quarter_turns)).astype(int)
        new = {}
        for (pos, n), col in self.stickers.items():
            if moving(pos, name):
                pos, n = tuple(int(v) for v in m @ pos), tuple(int(v) for v in m @ n)
            new[(pos, n)] = col
        self.stickers = new

    def solved(self):
        """Every face a single colour (whole-cube turns don't matter)."""
        faces = {}
        for (_, n), col in self.stickers.items():
            faces.setdefault(n, set()).add(col)
        return all(len(cols) == 1 for cols in faces.values())


# ----------------------------------------------------------------- the sealed flag
# The flag is never stored as text: it is XOR-ed with a keystream derived from
# the solved cube, and decoded only from the live cube once it is solved (any
# other state gives a different key, so garbage). seal_flag.py makes the
# sealed bytes.
def _centres(cube):
    return tuple(cube.stickers[(n, n)] for n in sorted(COLORS))


def state_key(cube):
    """SHA-256 of the cube's stickers, after turning the whole cube so its
    centres sit as in a fresh cube (so a solved cube gives the same key in
    any orientation)."""
    target, todo, seen = _centres(Cube()), [cube], set()
    while todo:  # the 24 whole-cube orientations, until the centres line up
        c = todo.pop()
        if _centres(c) == target:
            break
        if _centres(c) in seen:
            continue
        seen.add(_centres(c))
        for m in ("x", "y"):
            turned = Cube()
            turned.stickers = dict(c.stickers)
            turned.apply(m)
            todo.append(turned)
    return hashlib.sha256(repr(sorted(c.stickers.items())).encode()).digest()


def xor_stream(key, data):
    """data XOR a keystream from the key (the same call seals and unseals)."""
    return bytes(a ^ b for a, b in zip(data, hashlib.shake_256(key).digest(len(data))))


def reveal_flag(cube):
    return xor_stream(state_key(cube), FLAG_SEALED).decode("utf-8", "replace")


def _centre(axis):
    """Centre of an axis's circle family: toward where that axis's near face
    shows up in a corner view (screen coordinates, y down)."""
    sv = np.sign(VIEW[axis])
    d = sv * np.array([RIGHT[axis], -UP[axis]])
    return d / np.linalg.norm(d)


CENTRES = [_centre(a) for a in range(3)]


def ring_radius(axis, layer):
    """Radius of the circle holding the ring of stickers in that layer."""
    return RADII[1 - layer * int(np.sign(VIEW[axis]))]


def sticker_xy(pos, n):
    """Where a sticker's dot sits in the (unscaled) 2D picture."""
    a = int(np.argmax(np.abs(n)))
    b, c = [(1, 2), (2, 0), (0, 1)][a]
    cb, cc = CENTRES[b], CENTRES[c]
    rb, rc = ring_radius(b, pos[b]), ring_radius(c, pos[c])
    d = np.linalg.norm(cc - cb)
    e = (cc - cb) / d
    perp = np.array([-e[1], e[0]])
    t = (d * d + rb * rb - rc * rc) / (2 * d)
    h = np.sqrt(max(0.0, rb * rb - t * t))
    side = np.sign((CENTRES[a] - cb) @ perp)  # inner crossing, toward CENTRES[a]
    if n[a] * VIEW[a] < 0:  # far face: outer crossing
        side = -side
    return cb + t * e + side * h * perp


def turn_sense(axis, total_deg, n):
    """+1 / -1: which way (in screen angle) a dot travels around its pivot
    when turning about `axis`. Ring dots and the near faces turn one way,
    the far faces are drawn mirrored so they spin the other way."""
    if n[axis]:
        return -np.sign(total_deg) * np.sign(n[axis])
    return -np.sign(total_deg) * np.sign(VIEW[axis])


def turn_xy(q0, q1, pivot, sense, s):
    """Move a dot from q0 to q1 around `pivot` (fraction s of the turn),
    travelling in screen-angle direction `sense`. Ring dots keep their
    radius, so they slide exactly along their circle."""
    v0, v1 = q0 - pivot, q1 - pivot
    r0, r1 = np.hypot(*v0), np.hypot(*v1)
    if r0 < 1e-9:
        return q0
    f0, f1 = np.arctan2(v0[1], v0[0]), np.arctan2(v1[1], v1[0])
    delta = sense * ((sense * (f1 - f0)) % (2 * np.pi))
    f, r = f0 + delta * s, r0 + (r1 - r0) * s
    return pivot + r * np.array([np.cos(f), np.sin(f)])


# ----------------------------------------------------------------- drawing
def star_layers(r, half, line=1.0):
    """Alpha maps (size 2*half+1) of a sticker drawn as a star of radius r
    pixels: (coloured part: soft glow + translucent body, white part: bright
    core + faint 4-point spikes + rim). `line` is how many pixels of the map
    make one pixel on screen, so the rim and spikes stay visible when the map
    is drawn scaled down (as a GL texture)."""
    y, x = np.mgrid[-half:half + 1, -half:half + 1].astype(float)
    d = np.hypot(x, y)
    glow = 0.32 * np.clip(1 - (d - r) / (1.1 * r), 0, 1) ** 2 * (d > r)
    body = STAR_ALPHA * np.clip(r + 0.5 - d, 0, 1)
    colour = 1 - (1 - glow) * (1 - body)
    core = 0.85 * np.exp(-(d / (0.36 * r)) ** 2)
    reach = 2.2 * r
    w = 0.75 * line
    spikes = 0.5 * (np.exp(-(x / w) ** 2) * np.clip(1 - np.abs(y) / reach, 0, 1)
                    + np.exp(-(y / w) ** 2) * np.clip(1 - np.abs(x) / reach, 0, 1)) * (d > 0.8 * r)
    rim = 0.9 * np.clip(1 - np.abs(d - r) / (0.9 * line), 0, 1)
    white = 1 - (1 - core) * (1 - np.minimum(spikes, 1)) * (1 - rim)
    return colour, white


@functools.lru_cache(maxsize=4096)
def star_sprite(colour, r, fade=1.0):
    """A sticker as a little star (see star_layers) in its colour, as
    (pygame surface, half its size); `fade` scales its opacity."""
    import pygame
    r = max(2, r)
    half = int(np.ceil(r * 2.3)) + 1
    ca, wa = star_layers(r, half)
    a = wa + ca * (1 - wa)
    rgb = (255 * wa[..., None] + np.array(colour) * (ca * (1 - wa))[..., None]) \
        / np.maximum(a, 1e-6)[..., None]
    img = np.dstack([rgb, 255 * fade * a]).clip(0, 255).astype(np.uint8)
    spr = pygame.image.frombytes(img.tobytes(), (2 * half + 1,) * 2, "RGBA")
    if pygame.display.get_surface():  # match the screen's format: much faster blits
        spr = spr.convert_alpha()
    return spr, half


def draw_star(surface, colour, xy, r, fade=1.0):
    spr, half = star_sprite(tuple(colour), int(r), round(fade, 2))
    surface.blit(spr, (int(round(xy[0])) - half, int(round(xy[1])) - half))


class Sky:
    """Night-sky backdrop: a gradient with stars that twinkle softly and
    drift very slowly to the right (bigger, 'nearer' stars a bit faster)."""

    TINTS = ((255, 255, 255), (198, 214, 255), (255, 234, 200))
    DRIFT = 0.6  # pixels per second per unit of star size

    def __init__(self, width, height, seed=7):
        import pygame
        self.pg = pygame
        self.w, self.h = width, height
        t = np.linspace(0, 1, height)[:, None]
        self.rows = np.array(SKY_TOP) * (1 - t) + np.array(SKY_BOTTOM) * t
        grad = np.broadcast_to(self.rows[None], (width, height, 3))
        self.base = pygame.surfarray.make_surface(np.ascontiguousarray(grad, dtype=np.uint8))
        rng = np.random.default_rng(seed)
        n = width * height // 1200
        self.xy = rng.uniform(0, 1, (n, 2)) * (width, height)
        self.size = rng.choice((1, 1, 1, 1, 2, 2, 3), n)
        self.level = rng.uniform(0.3, 0.85, n) + 0.05 * self.size
        self.speed = rng.uniform(0.4, 1.8, n)
        self.phase = rng.uniform(0, 2 * np.pi, n)
        self.tint = np.array(self.TINTS)[rng.choice(3, n, p=(0.6, 0.25, 0.15))]
        # the pixels each star lights: (star, dx, dy, brightness factor);
        # bigger stars get a soft plus, the biggest a faint halo around that
        plus = ((1, 0), (-1, 0), (0, 1), (0, -1))
        halo = ((1, 1), (-1, 1), (1, -1), (-1, -1), (2, 0), (-2, 0), (0, 2), (0, -2))
        px = []
        for i, size in enumerate(self.size):
            px.append((i, 0, 0, 1.0))
            if size > 1:
                px += [(i, dx, dy, 0.45 if size == 2 else 0.7) for dx, dy in plus]
            if size > 2:
                px += [(i, dx, dy, 0.25) for dx, dy in halo]
        px = np.array(px)
        self.px_star = px[:, 0].astype(int)
        self.px_dx, self.px_dy, self.px_f = px[:, 1].astype(int), px[:, 2].astype(int), px[:, 3]

    def draw(self, surface, t):
        surface.blit(self.base, (0, 0))
        level = self.level * (0.7 + 0.3 * np.sin(self.speed * t + self.phase))
        xs = ((self.xy[:, 0] + t * self.DRIFT * self.size) % self.w).astype(int)
        ys = self.xy[:, 1].astype(int)
        i = self.px_star
        x = (xs[i] + self.px_dx) % self.w
        y = np.clip(ys[i] + self.px_dy, 0, self.h - 1)
        bg = self.rows[y]
        mix = np.minimum(1.0, level[i] * self.px_f)[:, None]
        pixels = self.pg.surfarray.pixels3d(surface)
        pixels[x, y] = (bg + (self.tint[i] - bg) * mix).astype(np.uint8)
        del pixels  # unlock the surface


class Scene:
    def __init__(self, width=960, height=480, show3d=True):
        import pygame
        import pygame.gfxdraw
        self.pg = pygame
        self.w, self.h = width, height
        self.surface = pygame.Surface((width, height))
        self.c3 = np.array([width * 0.73, height * 0.5])
        self.zoom2, self.c2 = 1.0, np.zeros(2)
        self.scale3 = height * 0.125
        self.show3d = show3d
        self.sky = Sky(width, height)
        self.time = 0.0  # seconds, for the sky's animation
        self.fit(Cube())

    def anchor2(self):
        """Screen point the 2D view is centred on: middle of the left half
        next to the 3D cube, or the middle of the window without it."""
        return np.array([self.w * (0.25 if self.show3d else 0.5), self.h * 0.5])

    def toggle_3d(self):
        self.show3d = not self.show3d
        self.fit(Cube())

    def project(self, xy):
        return np.atleast_2d(xy) * self.zoom2 + self.c2

    def set_zoom(self, factor):
        self.zoom2 = float(np.clip(self.zoom2 * factor, self.h * 0.03, self.h * 20))
        a = self.anchor2()
        self.c2 = (self.c2 - a) * factor + a
        self._size_dots()

    def fit(self, cube):
        """Zoom and centre the 2D view so every circle fits in its area."""
        r = RADII[2]
        lo = np.min([c - r for c in CENTRES], axis=0)
        hi = np.max([c + r for c in CENTRES], axis=0)
        span = 0.48 if self.show3d else 0.96
        self.zoom2 = min(self.w * span / (hi - lo)[0], self.h * 0.94 / (hi - lo)[1])
        self.c2 = self.anchor2() - (lo + hi) / 2 * self.zoom2
        self._size_dots()

    def _size_dots(self):
        xy = self.project([sticker_xy(p, n) for p, n in Cube().stickers])
        d = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(len(xy)) * 1e9
        self.dot = max(3, int(round(0.31 * d.min())))

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

    def draw(self, cube, move=None, angle=0.0, total=None):
        pg = self.pg
        s = self.surface
        self.sky.draw(s, self.time)
        rot = rotation(MOVES[move][0], angle) if move else np.eye(3)
        lim = 4 * max(self.w, self.h)

        # ---- 2D: rings (middle layer faint, as in the reference), then dots
        for a in range(3):
            c = self.project(CENTRES[a])[0]
            for r, (col, width) in zip(RADII, RING_STYLE):
                if np.all(np.abs(c) < lim) and r * self.zoom2 < lim:
                    self._circle(col, c, int(round(r * self.zoom2)), width)
        dots = []
        if move:
            ax = MOVES[move][0]
            snap = np.rint(rotation(ax, total)).astype(int)
        for (pos, n), col in cube.stickers.items():
            q = sticker_xy(pos, n)
            busy = move and moving(pos, move)
            if busy:
                q1 = sticker_xy(tuple(snap @ pos), tuple(snap @ n))
                # face dots spin around their face's centre dot, ring dots
                # slide along their axis's circles
                pivot = sticker_xy(n, n) if n[ax] else CENTRES[ax]
                q = turn_xy(q, q1, pivot, turn_sense(ax, total, n), angle / total)
            dots.append((bool(busy), q, col))
        dots.sort(key=lambda d: d[0])  # moving dots on top
        for _, q, col in dots:
            x, y = self.project(q)[0]
            if abs(x) < lim and abs(y) < lim:
                draw_star(s, col, (x, y), self.dot)

        if not self.show3d:
            return s

        # ---- 3D: cubies, far slab to near slab, far cubie to near cubie
        axis = MOVES[move][0] if move else 0
        toward = np.sign(EYE3[axis])
        faces = [np.array(v) for v in
                 [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
        cubies = []
        for p in np.ndindex(3, 3, 3):
            pos = tuple(v - 1 for v in p)
            if pos == (0, 0, 0):
                continue
            m = rot if (move and moving(pos, move)) else np.eye(3)
            centre = m @ np.array(pos, dtype=float)
            cubies.append((pos[axis] * toward, -np.linalg.norm(EYE3 - centre), pos, m, centre))
        cubies.sort(key=lambda c: (c[0], c[1]))
        for _, _, pos, m, centre in cubies:
            for n in faces:
                nw = m @ n
                fc = centre + 0.5 * nw
                if (EYE3 - fc) @ nw <= 1e-9:
                    continue
                u = np.roll(n, 1)
                v = np.cross(n, u)
                u, v = m @ u, m @ v
                self._quad(fc, u, v, 0.5, EDGE + (120,))  # dark glass cubie
                col = cube.stickers.get((pos, tuple(int(x) for x in n)))
                if col:  # translucent sticker, white outline
                    self._quad(fc + 0.002 * nw, u, v, 0.43, col + (int(255 * STAR_ALPHA) + 20,),
                               INK + (255,))
        return s

    def _quad(self, c, u, v, h, col, outline=None):
        pts = [c + h * (su * u + sv * v) for su, sv in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        xy = []
        for p in pts:
            k = self.scale3 * 10.0 / (10.0 - p @ VIEW3)  # perspective
            xy.append((int(round(p @ RIGHT3 * k + self.c3[0])),
                       int(round(-(p @ UP3) * k + self.c3[1]))))
        if len(col) == 4:  # with alpha: blend over what's there
            self.pg.gfxdraw.filled_polygon(self.surface, xy, col)
        else:
            self.pg.draw.polygon(self.surface, col, xy)
        if outline:
            self.pg.gfxdraw.aapolygon(self.surface, xy, outline)


def smooth(t):
    return t * t * (3 - 2 * t)


def animate(scene, cube, name, q, steps):
    """Yield surfaces animating one move, then apply it to the cube."""
    total = MOVES[name][2] * q
    n = steps * abs(q)
    for k in range(1, n):
        yield scene.draw(cube, name, total * smooth(k / n), total)
    cube.apply(name, q)
    yield scene.draw(cube)


def scramble(length=20, rng=random):
    seq, last = [], None
    for _ in range(length):
        n = rng.choice([m for m in "UDLRFB" if m != last])
        seq.append((n, rng.choice([1, -1, 2])))
        last = n
    return seq


# ----------------------------------------------------------------- outputs
def save_gif(seq, path, width=640, steps=12, debug=False):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from PIL import Image

    pygame.init()
    scene, cube = Scene(width, width // 2, show3d=debug), Cube()

    def grab(surf):
        return Image.fromarray(pygame.surfarray.array3d(surf).transpose(1, 0, 2))

    frames = []

    def still(count):
        for _ in range(count):
            scene.time = len(frames) / 30
            frames.append(grab(scene.draw(cube)))

    still(10)
    for name, q in seq:
        for f in animate(scene, cube, name, q, steps):
            frames.append(grab(f))
            scene.time = len(frames) / 30
        still(3)
    still(15)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0)
    print(f"saved {path} ({len(frames)} frames)")


class TextFont:
    """Stand-in for pygame.font.Font (render / size / get_linesize) that
    draws with Pillow, for pygame builds whose font module is broken (e.g.
    pygame 2.6 on Python 3.14)."""

    def __init__(self, size):
        from PIL import ImageFont
        self.font = ImageFont.load_default(size)
        ascent, descent = self.font.getmetrics()
        self.height = ascent + descent
        self.cache = {}

    def size(self, text):
        return int(self.font.getlength(text)) + 1, self.height

    def get_linesize(self):
        return self.height

    def render(self, text, antialias, color):
        key = (text, tuple(color))
        if key not in self.cache:
            import pygame
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", self.size(text), tuple(color[:3]) + (0,))
            ImageDraw.Draw(img).text((0, 0), text, font=self.font, fill=tuple(color[:3]) + (255,))
            self.cache[key] = pygame.image.frombytes(img.tobytes(), img.size, "RGBA")
        return self.cache[key]


def load_font(size):
    """pygame's font if it works, else Pillow's, else None (the UI then
    draws without text)."""
    try:
        import pygame.font
        pygame.font.init()
        return pygame.font.Font(None, size)
    except (ImportError, NotImplementedError, RuntimeError):
        pass
    try:
        return TextFont(size)
    except (ImportError, OSError):
        return None


def button_rect(pad, height, font, label="Randomize"):
    """The Randomize button's rect, wide enough for its label."""
    import pygame
    h = height // 12
    return pygame.Rect(pad, pad, h + font.size(label)[0] + h // 3 if font else h, h)


def draw_button(screen, rect, label, font, hover):
    """Rounded button with a die icon (and a label when fonts work)."""
    import pygame
    pygame.draw.rect(screen, (235, 215, 195) if hover else (250, 245, 238), rect, border_radius=8)
    pygame.draw.rect(screen, (160, 151, 143), rect, 2, border_radius=8)
    d = rect.h - 2 * max(4, rect.h // 6)
    die = pygame.Rect(0, 0, d, d)
    die.midleft = (rect.x + (rect.h - d) // 2 if font else rect.centerx - d // 2, rect.centery)
    pygame.draw.rect(screen, (255, 255, 255), die, border_radius=d // 5)
    pygame.draw.rect(screen, EDGE, die, 2, border_radius=d // 5)
    for fx, fy in ((0.28, 0.28), (0.72, 0.28), (0.5, 0.5), (0.28, 0.72), (0.72, 0.72)):
        pygame.draw.circle(screen, EDGE, (die.x + fx * d, die.y + fy * d), max(2, d // 10))
    if font:
        text = font.render(label, True, EDGE)
        screen.blit(text, text.get_rect(midleft=(die.right + (rect.h - d) // 2, rect.centery)))


def draw_flag(screen, x, y, size, font):
    """A little pennant on a pole, top-left corner of the pole at (x, y)."""
    import pygame
    pole = pygame.Rect(x, y, max(3, size // 12), size)
    pygame.draw.rect(screen, (200, 190, 180), pole)
    pygame.draw.circle(screen, (200, 190, 180), (pole.centerx, y), pole.w)
    cloth = [(pole.right, y + 2), (pole.right + size * 0.75, y + size * 0.2),
             (pole.right, y + size * 0.42)]
    pygame.draw.polygon(screen, (20, 200, 40), cloth)
    pygame.draw.polygon(screen, EDGE, cloth, 2)
    if font:
        text = font.render("SOLVED", True, INK)
        screen.blit(text, text.get_rect(midtop=(x + size * 0.35, y + size + 6)))


FLAG_SEALED = bytes.fromhex("284f75484a178984288b8ba55275d6dfa332c95e2210245e9a")  # the flag, sealed by seal_flag.py (see reveal_flag)
SEED = 42                    # the starting scramble: the same every game
START_MESSAGE = "Calibrate ship to this position"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
START_IMAGE = os.path.join(ASSETS, "cube_solved.png")

KEY_INK = (150, 200, 255)   # key names on the controls screen
HINT_INK = (140, 148, 182)  # the "press Esc" hint


def draw_hint(screen, font, text="Press Esc for controls"):
    """A quiet one-line hint at the bottom centre of the window."""
    if font:
        w, h = screen.get_size()
        t = font.render(text, True, HINT_INK)
        screen.blit(t, t.get_rect(midbottom=(w // 2, h - max(6, h // 60))))


def help_columns(rows, n):
    """Split rows into n even columns, never ending a column on a heading."""
    per = -(-len(rows) // n)
    cols = [rows[i:i + per] for i in range(0, len(rows), per)]
    for a, b in zip(cols, cols[1:]):
        while a and a[-1][1] is None:
            b.insert(0, a.pop())
    return cols


font_of_size = functools.lru_cache(maxsize=None)(lambda size: load_font(size))


def draw_help(screen, rows, size, title="Controls"):
    """Controls screen over a dimmed window: `rows` are (keys, action) pairs,
    and a row with action None is a section heading. Uses the fewest columns,
    then the biggest font (from `size` down), that fits the window."""
    import pygame
    w, h = screen.get_size()
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    screen.blit(shade, (0, 0))
    for fs in range(size, 9, -1):
        font, title_font = font_of_size(fs), font_of_size(fs * 2)
        if not (font and title_font):
            return
        lh = int(font.get_linesize() * 1.3)
        pad = lh
        key_w = max(font.size(k)[0] for k, a in rows if a) + lh
        col_w = max(key_w + font.size(a)[0] if a else font.size(k)[0] for k, a in rows)
        title_h = int(title_font.get_linesize() * 1.4)
        for n in range(1, 5):
            cols = help_columns(rows, n)
            panel = pygame.Rect(0, 0, len(cols) * col_w + (len(cols) + 1) * 2 * pad,
                                title_h + max(map(len, cols)) * lh + 2 * pad + lh)
            if panel.w <= w * 0.96 and panel.h <= h * 0.94:
                break
        else:
            continue
        break
    panel.center = (w // 2, h // 2)
    pygame.draw.rect(screen, (10, 11, 26), panel, border_radius=14)
    pygame.draw.rect(screen, RING_STYLE[1][0], panel, 2, border_radius=14)
    t = title_font.render(title, True, INK)
    screen.blit(t, t.get_rect(midtop=(panel.centerx, panel.y + pad // 2)))
    for c, col in enumerate(cols):
        x, y = panel.x + 2 * pad + c * (col_w + 2 * pad), panel.y + pad // 2 + title_h
        for keys, action in col:
            if action is None:  # section heading
                screen.blit(font.render(keys, True, HINT_INK), (x, y + lh // 4))
            else:
                screen.blit(font.render(keys, True, KEY_INK), (x, y))
                screen.blit(font.render(action, True, INK), (x + key_w, y))
            y += lh
    t = font.render("Esc  close        Q  quit", True, HINT_INK)
    screen.blit(t, t.get_rect(midbottom=(panel.centerx, panel.bottom - pad // 2)))


def draw_solved(screen, flag, size, message="The control panel has been recalibrated"):
    """The solved screen, styled like the controls screen: the message, then
    the flag."""
    import pygame
    w, h = screen.get_size()
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    screen.blit(shade, (0, 0))
    for fs in range(size, 9, -1):  # the biggest text that fits
        font, title_font = font_of_size(fs), font_of_size(fs * 2)
        if not (font and title_font):
            return
        pad = int(font.get_linesize() * 1.3)
        lines = [(title_font, "Solved!", INK), (font, message, INK),
                 (title_font, flag, KEY_INK), (font, "Esc  close        Q  quit", HINT_INK)]
        panel = pygame.Rect(0, 0, max(f.size(t)[0] for f, t, _ in lines) + 4 * pad,
                            sum(f.get_linesize() for f, _, _ in lines) + 4 * pad)
        if panel.w <= w * 0.96 and panel.h <= h * 0.94:
            break
    panel.center = (w // 2, h // 2)
    pygame.draw.rect(screen, (10, 11, 26), panel, border_radius=14)
    pygame.draw.rect(screen, RING_STYLE[1][0], panel, 2, border_radius=14)
    y = panel.y + pad
    for k, (f, text, colour) in enumerate(lines):
        y += pad * (k == 2) + pad // 2 * (k == 3)  # room around the flag
        t = f.render(text, True, colour)
        screen.blit(t, t.get_rect(midtop=(panel.centerx, y)))
        y += f.get_linesize()


def draw_start(screen, image, size, message, footer="Press any key to begin"):
    """Start screen, styled like the controls screen: the message over a
    picture (a pygame surface, shrunk to fit), then how to begin."""
    import pygame
    w, h = screen.get_size()
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 200))
    screen.blit(shade, (0, 0))
    font, title_font = font_of_size(size), font_of_size(int(size * 1.6))
    if not (font and title_font):
        screen.blit(image, image.get_rect(center=(w // 2, h // 2)))
        return
    pad = int(font.get_linesize() * 0.9)
    text_h = title_font.get_linesize() + font.get_linesize() + 4 * pad
    scale = min(1.0, (h * 0.96 - text_h) / image.get_height(),
                (w * 0.92 - 2 * pad) / image.get_width())
    if scale < 1:
        image = pygame.transform.smoothscale(
            image, (int(image.get_width() * scale), int(image.get_height() * scale)))
    panel = pygame.Rect(0, 0, max(image.get_width(), title_font.size(message)[0]) + 2 * pad,
                        image.get_height() + text_h)
    panel.center = (w // 2, h // 2)
    pygame.draw.rect(screen, (10, 11, 26), panel, border_radius=14)
    pygame.draw.rect(screen, RING_STYLE[1][0], panel, 2, border_radius=14)
    t = title_font.render(message, True, INK)
    screen.blit(t, t.get_rect(midtop=(panel.centerx, panel.y + pad)))
    top = panel.y + 2 * pad + title_font.get_linesize()
    screen.blit(image, image.get_rect(midtop=(panel.centerx, top)))
    t = font.render(footer, True, HINT_INK)
    screen.blit(t, t.get_rect(midbottom=(panel.centerx, panel.bottom - pad)))


def surface_from_pil(img):
    import pygame
    img = img.convert("RGB")
    return pygame.image.frombytes(img.tobytes(), img.size, "RGB")


def load_start_image(path=START_IMAGE):
    """The start screen's picture of the solved cube (the circles only, so
    it doesn't give away that it's a Rubik's cube), made with the game's own
    drawing if the file is missing."""
    from PIL import Image
    if not os.path.exists(path):
        make_start_image(path)
    return surface_from_pil(Image.open(path))


def make_start_image(path=START_IMAGE, width=560, height=480):
    import pygame
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene = Scene(width, height, show3d=False)
    surf = scene.draw(Cube())
    Image.fromarray(pygame.surfarray.array3d(surf).transpose(1, 0, 2)).save(path)


def help_rows(debug):
    rows = [("Turns", None),
            ("U D L R F B", "orbit turns"),
            ("M E S", "central orbit turns"),
            ("X Y Z", "rotate system"),
            ("Shift + key", "inverse (U')"),
            ("View", None),
            ("Mouse wheel", "zoom the circles")]
    if debug:
        rows += [("Tab", "show/hide the 3D cube"),
                 ("Space", "solve (debug only)")]
    return rows + [("Esc", "show/hide this screen"), ("Q", "quit")]


def run_window(initial=(), width=960, debug=False):
    import pygame

    pygame.init()
    height = width // 2
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("RASA Calibration Panel")
    clock = pygame.time.Clock()
    scene, cube = Scene(width, height, show3d=debug), Cube()
    for name, q in scramble(rng=random.Random(SEED)):  # every game starts scrambled
        cube.apply(name, q)
    small = load_font(max(14, height // 28))
    queue, anim = list(initial), None
    keymap = {getattr(pygame, f"K_{k.lower()}"): k for k in MOVES}
    show_help = show_solved = was_solved = False
    start_image, show_start = load_start_image(), True  # until any key or click

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif show_start:
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    show_start = False  # (the press only closes the start screen)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    running = False
                elif ev.key == pygame.K_ESCAPE:
                    if show_solved:
                        show_solved = False
                    else:
                        show_help = not show_help
                elif show_help or show_solved:
                    pass  # those screens take no other keys
                elif ev.key == pygame.K_SPACE and debug:  # a fresh, solved cube
                    queue, anim = [], None
                    cube.reset()
                elif ev.key == pygame.K_TAB and debug:
                    scene.toggle_3d()
                elif ev.key in keymap:
                    queue.append((keymap[ev.key], -1 if ev.mod & pygame.KMOD_SHIFT else 1))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                show_help = show_solved = False
            elif ev.type == pygame.MOUSEWHEEL and not (show_help or show_solved):
                scene.set_zoom(1.1 ** ev.y)

        scene.time = pygame.time.get_ticks() / 1000
        if anim is None and queue:
            name, q = queue.pop(0)
            anim = animate(scene, cube, name, q, 5 if len(queue) > 3 else 14)
        if anim is not None:
            try:
                frame = next(anim)
            except StopIteration:
                anim = None
        if anim is None:  # redraw every frame: the sky is animated
            frame = scene.draw(cube)

        solved = anim is None and not queue and cube.solved()
        if solved and not was_solved:  # just solved: show the flag
            show_solved, show_help = True, False
        was_solved = solved

        screen.blit(frame, (0, 0))
        if show_start:
            draw_start(screen, start_image, max(14, height // 28), START_MESSAGE)
        elif show_solved:
            draw_solved(screen, reveal_flag(cube), max(14, height // 24))
        elif show_help:
            draw_help(screen, help_rows(debug), max(14, height // 28))
        else:
            draw_hint(screen, small)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


# Public competitor build. When True, the hidden --debug flag (which enables the
# 3D view, Tab, and Space = instant solve) is not registered at all, so the
# shipped binary cannot be coaxed into solving itself. GM-only debug builds flip
# this to False and are never shipped in dist/.
PUBLIC_BUILD = True

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RASA calibration panel")
    ap.add_argument("moves", nargs="?", default="", help="e.g. \"R U R' U'\"")
    ap.add_argument("--gif", help="write an animated GIF instead of opening a window")
    ap.add_argument("--width", type=int, default=None)
    if not PUBLIC_BUILD:
        # --debug (debug view, Tab, Space-solve) works but is left out of --help
        ap.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    debug = getattr(args, "debug", False)
    seq = parse(args.moves)
    if args.gif:
        save_gif(seq or scramble(12), args.gif, width=args.width or 640, debug=debug)
    else:
        run_window(seq, width=args.width or 960, debug=debug)