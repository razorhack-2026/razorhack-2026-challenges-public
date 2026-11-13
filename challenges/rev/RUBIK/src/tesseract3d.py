"""
4D Rubik's cube (3x3x3x3 tesseract), rendered in real 3D with OpenGL.

Same puzzle, moves, controls and two views as tesseract2d.py (which this
imports the puzzle from), but drawn with lighting, a depth buffer and depth
fog instead of flat circles:

  rings view   every sticker sits where the spheres of its three other-axis
               layers meet (the spheres themselves aren't drawn, but turning
               stickers still roll along them). Each cell is a "galaxy" of one
               3D shape - R cube, L tetrahedron, U star, D ringed sphere,
               F torus, B octahedron, O dodecahedron, I double-ringed sphere -
               and is also a regular Rubik's cube: each sticker is a cubie,
               its outward sides coloured U white, D yellow, F green, B blue,
               R red, L orange (as that cell's focus keys see it). Solved means
               every galaxy is home AND every cube's faces are one colour.
               The focused cell is drawn as a 3x3x3 lattice.

Controls (the keys are rubik2d's, applied to the focused cell as if it were
a 3D cube, oriented as it looks in the debug view):
    click a shape/sticker, a galaxy button, or 1-8   focus that cell
                  (hover a button for its galaxy's name)
    Ctrl + click a shape or galaxy button: show only that galaxy, centred
                  (Ctrl + click it again, or empty space, to show all)
    U D L R F B   orbit turns         M E S   central orbit turns
    X Y Z         rotate system: the whole focused cell (a real 4D twist)
    hold Shift for the inverse, Ctrl to turn the whole puzzle instead
    Mouse drag    orbit the view      Mouse wheel  zoom the view under it
    G             lattice on every cell, not just the focused one
    H             show/hide the O cell in the debug view
    Esc           show/hide the controls screen        Q  quit
    The tesseract starts scrambled; solving it shows the flag. A start screen
    (assets/tesseract_solved.gif: one turn around the solved tesseract,
    recorded if missing) plays until any key or click.

Usage:
    python tesseract3d.py                      # interactive, starts scrambled
    python tesseract3d.py "RU FO' *RO 2UF"     # scrambled, then play a sequence
    python tesseract3d.py --debug              # also show the 4D debug view
    python tesseract3d.py "RU" --gif t.gif     # render a GIF (needs Pillow)

Requires numpy, pygame and PyOpenGL (plus Pillow for --gif).
"""

import argparse
import os
import random

import numpy as np
from OpenGL.GL import *  # noqa: F403 (the GL API is a flat namespace)

from rubik2d import (ASSETS, BG, INK, MOVES as MOVES3, RING_STYLE, Sky, draw_help,
                     draw_hint, draw_solved, draw_start, load_font, smooth, star_layers,
                     surface_from_pil, xor_stream)
from tesseract2d import (CELLS, KEYS, VERTS, FACES, Tesseract, local_face,
                         fade, focus_buttons, focus_move, help_rows, move_matrix,
                         moving, normal, parse, project4, ring_pivot, scramble, state_key,
                         sticker_xyz,
                         turn_xyz)

FOV = 30.0  # vertical field of view, degrees
FLAG_SEALED = bytes.fromhex("095c423b8e7fe7f5d036871600c58b4e76423002d8a7edcd784ab7")  # the flag, sealed by seal_flag.py --tesseract (see reveal_flag)
SEED = 42                    # the starting scramble: the same every game
START_MESSAGE = "Calibrate console to this position"
START_GIF = os.path.join(ASSETS, "tesseract_solved.gif")


def reveal_flag(tess):
    """The flag, unsealed with a key from the tesseract's state: right only
    when it is solved (see tesseract2d.state_key and seal_flag.py)."""
    return xor_stream(state_key(tess), FLAG_SEALED).decode("utf-8", "replace")


def rgb(col, alpha=None):
    c = [v / 255 for v in col]
    return c if alpha is None else c + [alpha]


# ----------------------------------------------------------------- meshes and matrices
STAR_HALF = 63                      # star texture: 127 px square per layer
STAR_R = (STAR_HALF - 1) / 2.3      # the star's radius in texture pixels
STAR_EXTENT = STAR_HALF / STAR_R    # quad half-size in units of the star's radius


def star_texture():
    """One GL texture holding a star's two layers side by side (white RGB,
    alpha = coloured part | white part); drawing a star is a quad of each,
    the first tinted with the sticker's colour."""
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    alpha = np.hstack(star_layers(STAR_R, STAR_HALF, line=STAR_R / 7))  # drawn ~7 px across
    img = np.dstack([np.full(alpha.shape + (3,), 255.0), 255 * alpha]).astype(np.uint8)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.shape[1], img.shape[0], 0, GL_RGBA,
                 GL_UNSIGNED_BYTE, np.ascontiguousarray(img))
    return tex


# ----------------------------------------------------------------- sticker shapes
# Each cell is a "galaxy": its stickers are drawn as its own 3D shape (which
# travels with them), painted like the cubies of a Rubik's cube.
SHAPE_OF_CELL = {
    "R": "cube", "L": "tetrahedron", "U": "star", "D": "ringed sphere",
    "F": "torus", "B": "octahedron", "O": "dodecahedron", "I": "double-ringed sphere",
}
SPIN = 0.5  # radians per second every shape turns about the vertical
LOOKS_SMALL = {"tetrahedron": 1.3, "cube": 0.88}  # evens out how big the shapes look
REGIONS = "RLBFUD"         # paint regions 0-5: the part of a shape facing +x -x +y -y +z -z
PLAIN = 6                  # paint region 6: always NEUTRAL (inner sides)
FIXED = 7                  # paint region 7: always white (rings)
NEUTRAL = (40, 42, 56)     # a cubie's uncoloured sides (dark, like cube plastic)
SHAPE_FADE = 0.2           # how much shapes outside the focused cell fade (FADE is for 2D)
RING = (195, 200, 222)


def galaxy(shape):
    return shape.title() + " Galaxy"


def regions_of(points):
    """Paint region of each point: the face direction it lies furthest along."""
    a = np.argmax(np.abs(points), axis=-1)
    neg = np.take_along_axis(points, a[..., None], -1)[..., 0] < 0
    return 2 * a + neg


class Mesh:
    """A triangle soup (3 vertices per triangle, so each triangle can take its
    own colour) with normals, a paint region per vertex, and optional outline
    edges, scaled (unless told not to) to fit the unit sphere."""

    def __init__(self, verts, normals, region, edges=None, fit=True):
        verts = np.asarray(verts, dtype=float)
        scale = np.linalg.norm(verts, axis=1).max() if fit else 1.0
        self.verts = verts / scale
        self.normals = np.asarray(normals, dtype=float)
        self.region = np.asarray(region)
        self.edges = None if edges is None else np.asarray(edges, dtype=float) / scale

    @staticmethod
    def join(*meshes):
        return Mesh(np.concatenate([m.verts for m in meshes]),
                    np.concatenate([m.normals for m in meshes]),
                    np.concatenate([m.region for m in meshes]))

    def turned(self, m):
        out = Mesh(self.verts @ m.T, self.normals @ m.T, self.region, fit=False)
        out.edges = None if self.edges is None else self.edges @ m.T
        return out


def _subdivide(a, b, c, n):
    """Triangle abc cut into n*n smaller ones."""
    p = lambda i, j: a + (b - a) * i / n + (c - a) * j / n
    out = []
    for i in range(n):
        for j in range(n - i):
            out.append((p(i, j), p(i + 1, j), p(i, j + 1)))
            if i + j < n - 1:
                out.append((p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)))
    return out


def polyhedron(points, faces, cuts=1):
    """Flat-shaded mesh (with edges) from vertex points and convex faces given
    as vertex index lists in any order; each triangle is cut `cuts` times per
    side so the paint regions can follow the shape."""
    points = np.asarray(points, dtype=float)
    tris, normals, edges = [], [], []
    for face in faces:
        poly = points[list(face)]
        c = poly.mean(axis=0)
        n = c / np.linalg.norm(c)  # faces of these solids point away from the middle
        e1 = (poly[0] - c) / np.linalg.norm(poly[0] - c)
        poly = poly[np.argsort(np.arctan2((poly - c) @ np.cross(n, e1), (poly - c) @ e1))]
        for i in range(1, len(poly) - 1):
            for t in _subdivide(poly[0], poly[i], poly[i + 1], cuts):
                tris.append(t)
                normals.append([n] * 3)
        edges += [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    tris = np.array(tris)
    region = np.repeat(regions_of(tris.mean(axis=1)), 3)
    return Mesh(tris.reshape(-1, 3), np.reshape(normals, (-1, 3)), region, edges)


def surface(f, nu, nv, region=None):
    """Smooth mesh of a parametric surface f(u, v) -> (point, normal), u and v
    in [0, 1]; painted by position unless given one fixed region."""
    u, v = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    p, n = f(u, v)
    quads = [(p[i, j], p[i + 1, j], p[i, j + 1], p[i + 1, j + 1],
              n[i, j], n[i + 1, j], n[i, j + 1], n[i + 1, j + 1])
             for i in range(nu) for j in range(nv)]
    tris = np.array([t for q in quads for t in ((q[0], q[1], q[2]), (q[2], q[1], q[3]))])
    norms = np.array([t for q in quads for t in ((q[4], q[5], q[6]), (q[6], q[5], q[7]))])
    if region is None:
        region = np.repeat(regions_of(tris.mean(axis=1)), 3)
    else:
        region = np.full(len(tris) * 3, region)
    return Mesh(tris.reshape(-1, 3), norms.reshape(-1, 3), region, fit=False)


def sphere(r=1.0):
    def f(u, v):
        t, ph = np.pi * u, 2 * np.pi * v
        n = np.stack([np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.cos(t)], -1)
        return r * n, n
    return surface(f, 9, 16)


def torus(big, small, tilt=np.eye(3), region=None, around=24, sides=7):
    def f(u, v):
        a, b = 2 * np.pi * u, 2 * np.pi * v
        ring = np.stack([np.cos(a), np.sin(a), 0 * a], -1)
        n = np.cos(b)[..., None] * ring + np.sin(b)[..., None] * np.array([0, 0, 1.0])
        return (big * ring + small * n) @ tilt.T, n @ tilt.T
    return surface(f, around, sides, region)


def _tilt(axis, degrees):
    from rubik2d import rotation
    return rotation(axis, degrees)


def _dodecahedron():
    g = (1 + 5 ** 0.5) / 2
    pts = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    for a in (-1 / g, 1 / g):
        for b in (-g, g):
            pts += [(0, a, b), (a, b, 0), (b, 0, a)]
    pts = np.array(pts)
    # a face per icosahedron vertex direction: the 5 points furthest along it
    dirs = [np.roll((0, a, b), k) for a in (-1, 1) for b in (-g, g) for k in range(3)]
    return polyhedron(pts, [np.argsort(-(pts @ d))[:5] for d in dirs], cuts=2)


def _star(core=0.3):
    """Six spikes, one along each face direction, so each spike takes that
    face's colour (with outlines along the spikes)."""
    tris, normals, edges = [], [], []
    for a in range(3):
        for s in (1, -1):
            tip = np.zeros(3)
            tip[a] = s
            b, c = [k for k in range(3) if k != a]
            base = []
            for sb, sc in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                p = s * core * np.eye(3)[a]
                p[b], p[c] = sb * core, sc * core
                base.append(p)
            for i in range(4):
                t = np.array([tip, base[i], base[(i + 1) % 4]])
                n = np.cross(t[1] - t[0], t[2] - t[0])
                n *= np.sign(n @ t.mean(axis=0)) / np.linalg.norm(n)
                tris.append(t)
                normals.append([n] * 3)
                edges.append((tip, base[i]))
    tris = np.array(tris)
    return Mesh(tris.reshape(-1, 3), np.reshape(normals, (-1, 3)),
                np.repeat(regions_of(tris.mean(axis=1)), 3), edges)


def _shapes():
    cube = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    tetra = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    octa = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    ring = lambda tilt: torus(1.32, 0.05, tilt, FIXED, around=32, sides=4)
    tilt = _tilt(0, 20) @ _tilt(1, 15)  # so the solids aren't seen face-on
    return {
        "cube": polyhedron(cube, [[i for i, p in enumerate(cube) if p[a] == s]
                                  for a in range(3) for s in (-1, 1)]).turned(tilt),
        "tetrahedron": polyhedron(tetra, [[j for j in range(4) if j != i] for i in range(4)],
                                  cuts=5).turned(tilt),
        "star": _star().turned(tilt),
        "octahedron": polyhedron(octa, [[a, b, c] for a in (0, 1) for b in (2, 3)
                                        for c in (4, 5)], cuts=4).turned(tilt),
        "dodecahedron": _dodecahedron().turned(tilt),
        "torus": torus(0.68, 0.32, _tilt(0, 60)),  # (painted after the tilt: all six sides)
        "ringed sphere": Mesh.join(sphere(0.78), ring(_tilt(0, 70))),
        "double-ringed sphere": Mesh.join(sphere(0.72), ring(_tilt(0, 65)), ring(_tilt(1, 65))),
    }


SHAPES = _shapes()


ICONS = list(SHAPE_OF_CELL.values())  # order of the symbols in icon_texture
ICON_PX = 96


def icon_texture():
    """One GL texture with every galaxy's symbol side by side (white lines,
    alpha), for the faces of the debug view's little cubes."""
    import pygame
    atlas = pygame.Surface((ICON_PX * len(ICONS), ICON_PX), pygame.SRCALPHA)
    for k, shape in enumerate(ICONS):
        draw_galaxy_icon(atlas, shape, (ICON_PX * (k + 0.5), ICON_PX / 2), ICON_PX * 0.36, width=5)
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_GENERATE_MIPMAP, GL_TRUE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, atlas.get_width(), atlas.get_height(), 0, GL_RGBA,
                 GL_UNSIGNED_BYTE, pygame.image.tobytes(atlas, "RGBA", True))
    return tex


def _lattice():
    """Index pairs into KEYS of neighbouring stickers in the same cell: the
    edges of each cell's 3x3x3 grid."""
    where = {k: i for i, k in enumerate(KEYS)}
    out = []
    for i, (pos, n) in enumerate(KEYS):
        for a in range(4):
            if n[a] == 0 and pos[a] < 1:
                nxt = list(pos)
                nxt[a] += 1
                out.append((i, where[(tuple(nxt), n)]))
    return np.array(out)


LATTICE = _lattice()
CELL_OF_KEY = np.array([[c for c in CELLS if normal(c) == n][0] for _, n in KEYS])
CELL_POINTS = {c: np.array([sticker_xyz(p, n) for p, n in KEYS if n == normal(c)]) for c in CELLS}


def perspective(fovy, aspect, near, far):
    f = 1 / np.tan(np.radians(fovy) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3], m[3, 2] = (far + near) / (near - far), 2 * far * near / (near - far), -1
    return m


def look_at(eye, up, target=np.zeros(3)):
    """View matrix for a camera at `eye` looking at `target`."""
    f = (target - eye) / np.linalg.norm(target - eye)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, np.cross(s, f), -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def draw_arrays(mode, verts, normals=None, colors=None, indices=None, texcoords=None):
    """One draw call from numpy arrays (vertex/normal/colour/texcoord per vertex)."""
    verts = np.ascontiguousarray(verts, dtype=np.float32).reshape(-1, 3)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, verts)
    if texcoords is not None:
        texcoords = np.ascontiguousarray(texcoords, dtype=np.float32).reshape(-1, 2)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glTexCoordPointer(2, GL_FLOAT, 0, texcoords)
    if normals is not None:
        normals = np.ascontiguousarray(normals, dtype=np.float32).reshape(-1, 3)
        glEnableClientState(GL_NORMAL_ARRAY)
        glNormalPointer(GL_FLOAT, 0, normals)
    if colors is not None:
        colors = np.ascontiguousarray(colors, dtype=np.float32)
        colors = colors.reshape(-1, colors.shape[-1])
        glEnableClientState(GL_COLOR_ARRAY)
        glColorPointer(colors.shape[-1], GL_FLOAT, 0, colors)
    if indices is not None:
        indices = np.ascontiguousarray(indices, dtype=np.uint32).ravel()
        glDrawElements(mode, indices.size, GL_UNSIGNED_INT, indices)
    else:
        glDrawArrays(mode, 0, len(verts))
    for state in (GL_VERTEX_ARRAY, GL_NORMAL_ARRAY, GL_COLOR_ARRAY, GL_TEXTURE_COORD_ARRAY):
        glDisableClientState(state)


# ----------------------------------------------------------------- views
class View:
    """An orbiting perspective camera (z up) looking at a target point (the
    origin unless a galaxy is shown alone), drawing into a rectangle of the
    window (pygame coordinates, y down). Target and distance glide to their
    goals."""

    def __init__(self, extent, view):
        v = np.array(view, dtype=float)
        self.yaw = np.arctan2(v[1], v[0])
        self.pitch = np.arcsin(v[2] / np.linalg.norm(v))
        self.extent = extent
        self.rect = (0, 0, 1, 1)
        self.dist = self.goal_dist = 1.0
        self.target, self.goal_target = np.zeros(3), np.zeros(3)

    def fitting(self, extent):
        """Camera distance that fits a sphere of that radius in the view."""
        aspect = max(self.rect[2], 1) / self.rect[3]  # (a hidden view is 0 wide)
        return 1.08 * extent / np.tan(np.radians(FOV) / 2) / min(1.0, aspect)

    def place(self, rect):
        self.rect = rect
        self.dist = self.goal_dist = self.fitting(self.extent)

    def contains(self, xy):
        x, y, w, h = self.rect
        return x <= xy[0] < x + w and y <= xy[1] < y + h

    def orbit(self, dx, dy):
        self.yaw -= dx * 0.008
        self.pitch = float(np.clip(self.pitch + dy * 0.008, -1.5, 1.5))

    def zoom(self, factor):
        self.goal_dist = float(np.clip(self.goal_dist / factor, self.extent * 0.4, self.extent * 30))

    def eye(self):
        cp = np.cos(self.pitch)
        return self.target + self.dist * np.array(
            [cp * np.cos(self.yaw), cp * np.sin(self.yaw), np.sin(self.pitch)])

    def begin(self, win_h):
        """Point GL at this view: viewport, matrices, light, fog."""
        x, y, w, h = self.rect
        glViewport(x, win_h - y - h, w, h)
        glScissor(x, win_h - y - h, w, h)
        self.target += (self.goal_target - self.target) * 0.15  # glide
        self.dist += (self.goal_dist - self.dist) * 0.15
        eye = self.eye()
        up = np.array([0.0, 0.0, 1.0]) if abs(self.pitch) < 1.49 else np.array([0.0, 1.0, 0.0])
        self.proj = perspective(FOV, w / h, self.dist * 0.2, self.dist + self.extent * 6)
        self.model = look_at(eye, up, self.target)
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(self.proj.T.astype(np.float32))
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLightfv(GL_LIGHT0, GL_POSITION, (-0.45, 0.75, 1.0, 0.0))  # eye space: upper left
        glLoadMatrixf(self.model.T.astype(np.float32))
        glFogf(GL_FOG_START, self.dist - self.extent * 0.8)
        glFogf(GL_FOG_END, self.dist + self.extent * 6.0)

    def to_screen(self, pts):
        """World points -> (window xy, distance to the camera plane)."""
        x, y, w, h = self.rect
        p = np.c_[pts, np.ones(len(pts))] @ (self.proj @ self.model).T
        ndc = p[:, :2] / p[:, 3:]
        return np.c_[x + (ndc[:, 0] + 1) / 2 * w, y + (1 - ndc[:, 1]) / 2 * h], p[:, 3]

    def pixels(self, radius, depth):
        """On-screen size of a world-space radius at that depth."""
        return radius * self.rect[3] / 2 * self.proj[1, 1] / depth


class Scene:
    def __init__(self, width=1200, height=600, show3d=True, panel=0):
        self.w, self.h, self.panel = width, height, panel
        self.focus = "I"
        self.show_outer = False
        self.lattice_all = False
        self.highlight = True  # the focused cell stands out (off: all cells alike)
        self.solo = None       # a cell shown alone and centred (Ctrl+click), or None
        self._dist_before_solo = None
        self.time = 0.0  # seconds, for the shapes' spin
        pts = np.array([sticker_xyz(p, n) for p, n in KEYS])
        d = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(len(pts)) * 1e9
        self.ball = 0.3 * d.min()
        r = np.linalg.norm(project4(VERTS[[n[3] < 1 for _, n in KEYS]]), axis=-1).max()
        self.rings = View(np.linalg.norm(pts, axis=1).max() + self.ball, (0.3, -1.0, 0.35))
        self.debug = View(r, (1.0, -1.5, 1.15))
        self.show3d = show3d
        self.layout()
        self._picks = {}

        glClearColor(*rgb(BG), 1)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_SCISSOR_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.55, 0.55, 0.55, 1))  # bright shadows: clear colours
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.6, 0.6, 0.6, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (0.35, 0.35, 0.35, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.4, 0.4, 0.4, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 48)
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogfv(GL_FOG_COLOR, rgb(BG, 1))
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_MULTISAMPLE)
        self.star_tex = star_texture()
        self.icon_tex = icon_texture()

    def layout(self):
        split = self.w // 2 if self.show3d else self.w
        self.rings.place((self.panel, 0, split - self.panel, self.h))
        self.debug.place((split, 0, self.w - split, self.h))

    def set_solo(self, cell):
        """Show only `cell` (also focusing it), centred and zoomed to fit; the
        same cell again, or None, shows everything as before."""
        view = self.rings
        if cell is None or cell == self.solo:
            if self.solo:
                view.goal_target = np.zeros(3)
                view.goal_dist = self._dist_before_solo
            self.solo = None
            return
        if self.solo is None:
            self._dist_before_solo = view.goal_dist
        self.solo = self.focus = cell
        pts = CELL_POINTS[cell]
        view.goal_target = pts.mean(axis=0)
        view.goal_dist = view.fitting(np.linalg.norm(pts - pts.mean(axis=0), axis=1).max()
                                      + 2 * self.ball)

    def toggle_3d(self):
        self.show3d = not self.show3d
        self.layout()

    def view_at(self, xy):
        if self.show3d and self.debug.contains(xy):
            return self.debug
        return self.rings

    def pick(self, xy):
        """Cell of the nearest ball/sticker under a window point, or None."""
        view = self.view_at(xy)
        if view not in self._picks:
            return None
        pts, radius, cells = self._picks[view]
        sxy, depth = view.to_screen(pts)
        hit = np.linalg.norm(sxy - xy, axis=1) < np.maximum(view.pixels(radius, depth), 6)
        if not hit.any():
            return None
        return cells[np.flatnonzero(hit)[np.argmin(depth[hit])]]

    def draw(self, tess, move=None, angle=0.0, total=None, backdrop=None):
        glDisable(GL_SCISSOR_TEST)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_SCISSOR_TEST)
        if backdrop:
            backdrop()
        self._draw_rings(tess, move, angle, total)
        if self.show3d:
            self._draw_debug(tess, move, angle, total)

    # ---- rings view
    def _draw_rings(self, tess, move, angle, total):
        view = self.rings
        view.begin(self.h)
        focus = normal(self.focus)

        # ball positions, the moving ones part-way round
        pts = np.array([sticker_xyz(p, n) for p, n in KEYS])
        if move:
            snap = np.rint(move_matrix(move, total)).astype(int)
            quarter = np.rint(move_matrix(move, 90 * np.sign(total))).astype(int)
            for i, (pos, n) in enumerate(KEYS):
                if moving(pos, move):
                    q1 = sticker_xyz(tuple(snap @ pos), tuple(snap @ n))
                    qq = sticker_xyz(tuple(quarter @ pos), tuple(quarter @ n))
                    pts[i] = turn_xyz(pts[i], q1, qq, *ring_pivot(pos, n, move), angle / total)

        # shown alone: only that cell's stickers, plus any turning into it
        show = np.ones(len(KEYS), dtype=bool)
        if self.solo:
            home = normal(self.solo)
            show = np.array([n == home or (move is not None and moving(pos, move)
                                           and tuple(snap @ n) == home) for pos, n in KEYS])

        mine = np.array([n == focus or not self.highlight for _, n in KEYS])
        radius = np.where(mine, self.ball, self.ball * 0.78)
        self._picks[view] = (pts[show], radius[show], CELL_OF_KEY[show])

        # lattices (the focused cell's 3x3x3 grid)
        glDisable(GL_LIGHTING)
        same = mine[LATTICE[:, 0]]
        seen = show[LATTICE[:, 0]] & show[LATTICE[:, 1]]
        if self.lattice_all and self.highlight:
            glLineWidth(1.0)
            glColor3f(*rgb(fade(INK, 0.6)))
            draw_arrays(GL_LINES, pts[LATTICE[~same & seen]])
        if self.highlight:
            glLineWidth(2.5)
            glColor3f(*rgb(INK))
            draw_arrays(GL_LINES, pts[LATTICE[same & seen]])
        glEnable(GL_LIGHTING)

        # stickers as 3D shapes, one batch per shape, all spinning together,
        # each painted from its sticker's colours (see paint)
        a = SPIN * self.time
        spin = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        shape = np.array([SHAPE_OF_CELL[tess.home(k)] for k in KEYS])
        paint = self.paint(tess, mine)
        size = radius * 1.4
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1, 1)
        for name, mesh in SHAPES.items():
            sel = np.flatnonzero((shape == name) & show)
            if not len(sel):
                continue
            mv, mn = mesh.verts @ spin.T * LOOKS_SMALL.get(name, 1.0), mesh.normals @ spin.T
            verts = pts[sel, None] + size[sel, None, None] * mv
            draw_arrays(GL_TRIANGLES, verts, np.broadcast_to(mn, verts.shape),
                        paint[sel][:, mesh.region])
            if mesh.edges is not None:  # white outlines on the solids
                glDisable(GL_LIGHTING)
                glEnable(GL_BLEND)
                glLineWidth(1.3)
                edges = pts[sel, None, None] + size[sel, None, None, None] * (
                    mesh.edges @ spin.T * LOOKS_SMALL.get(name, 1.0))
                ink = np.empty(edges.shape[:-1] + (4,))
                ink[..., :3] = rgb(INK)
                ink[..., 3] = np.where(mine[sel], 0.9, 0.35)[:, None, None]
                draw_arrays(GL_LINES, edges, colors=ink)
                glDisable(GL_BLEND)
                glEnable(GL_LIGHTING)
        glDisable(GL_POLYGON_OFFSET_FILL)

        # the star galaxy also sparkles: the white layer (core, spikes, rim)
        # of the star texture on camera-facing quads around each 3D star
        stars = np.flatnonzero((shape == "star") & show)
        if not len(stars):
            return
        right, up = view.model[0, :3], view.model[1, :3]
        corners = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], dtype=float)
        ext = (radius * STAR_EXTENT * 1.15)[stars, None, None]
        verts = pts[stars, None] + ext * (corners[:, :1] * right + corners[:, 1:] * up)
        texcoords = np.broadcast_to((corners + 1) / 2 * [0.5, 1] + [0.5, 0], verts.shape[:2] + (2,))
        colors = np.ones(verts.shape[:2] + (4,))
        colors[..., 3] = np.where(mine[stars], 0.85, 0.4)[:, None]
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.star_tex)
        glEnable(GL_BLEND)
        glDepthMask(GL_FALSE)
        draw_arrays(GL_QUADS, verts, colors=colors, texcoords=texcoords)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

    def paint(self, tess, mine):
        """(216, 8, 3) colours of each sticker's paint regions: its coloured
        sides on the regions they face in the cell it's in now (as that
        cell's focus keys see it), the rest NEUTRAL, rings white; faded
        outside the focused cell."""
        out = np.empty((len(KEYS), 8, 3))
        out[:] = rgb(NEUTRAL)
        out[:, FIXED] = rgb(RING)
        for i, key in enumerate(KEYS):
            for d, c in tess.stickers[key][1]:
                out[i, REGIONS.index(local_face(CELL_OF_KEY[i], d))] = rgb(c)
        out[~mine] = out[~mine] * (1 - SHAPE_FADE) + np.array(rgb(BG)) * SHAPE_FADE
        return out

    # ---- debug view
    def _draw_debug(self, tess, move, angle, total):
        view = self.debug
        view.begin(self.h)
        verts = VERTS.copy()
        hide = np.array([n == normal("O") for _, n in KEYS])
        if move:
            busy = np.array([moving(p, move) for p, _ in KEYS])
            verts[busy] = verts[busy] @ move_matrix(move, angle).T
            snap = np.rint(move_matrix(move, total)).astype(int)
            # show stickers on their way in or out of O
            hide &= ~busy | np.array([tuple(snap @ n) == normal("O") for _, n in KEYS])
        if self.show_outer or self.focus == "O":
            hide[:] = False
        show = ~hide

        p3 = project4(verts)[show]                    # (k, 8, 3)
        quads = p3[:, FACES]                          # (k, 6, 4, 3)
        fc = quads.mean(axis=2)
        nrm = np.cross(quads[:, :, 1] - quads[:, :, 0], quads[:, :, 3] - quads[:, :, 0])
        out = np.einsum("sfk,sfk->sf", nrm, fc - p3.mean(axis=1)[:, None])
        nrm *= np.where(out < 0, -1.0, 1.0)[..., None]
        keys = [k for k, s in zip(KEYS, show) if s]
        focus = normal(self.focus)
        dim = np.array([k[1] != focus for k in keys])
        self._picks[view] = (p3.mean(axis=1), np.full(len(keys), 0.12), CELL_OF_KEY[show])

        # translucent faces, sorted far to near so they blend in order; each
        # little cube's faces are painted like a cubie (coloured sides, the
        # rest NEUTRAL)
        k = len(keys)
        cols = np.empty((k, 6, 4))
        for i, (pos, n) in enumerate(keys):
            facets = tess.facets((pos, n))
            rest = [x for x in range(4) if n[x] == 0]
            for f in range(6):
                d = tuple((1 if f % 2 else -1) * int(x == rest[f // 2]) for x in range(4))
                cols[i, f, :3] = rgb(facets.get(d, NEUTRAL))
        cols[dim, :, :3] = cols[dim, :, :3] * (1 - SHAPE_FADE) + np.array(rgb(BG)) * SHAPE_FADE
        cols[..., 3] = np.where(dim, 0.72, 0.92)[:, None]  # nearly solid: clear colours
        order = np.argsort(-np.linalg.norm(fc - view.eye(), axis=-1).ravel())
        faces = quads.reshape(-1, 4, 3)[order]
        glEnable(GL_BLEND)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1, 1)
        draw_arrays(GL_QUADS, faces, np.repeat(nrm.reshape(-1, 1, 3)[order], 4, axis=1),
                    np.repeat(cols.reshape(-1, 1, 4)[order], 4, axis=1))
        glDisable(GL_POLYGON_OFFSET_FILL)

        # each face shows the symbol of the sticker's home galaxy: dark on
        # light colours, light on dark ones, a little in from the edges and
        # just off the face
        glDisable(GL_LIGHTING)
        icon = np.array([ICONS.index(SHAPE_OF_CELL[tess.home(key)]) for key in keys])
        centre = quads.mean(axis=2, keepdims=True)
        unit = nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)
        art = centre + (quads - centre) * 0.8 + unit[:, :, None] * 0.004   # (k, 6, 4, 3)
        u0 = icon / len(ICONS)
        uv = np.empty((k, 6, 4, 2))
        uv[..., 0] = u0[:, None, None] + np.array([0, 1, 1, 0]) / len(ICONS)
        uv[..., 1] = np.array([0, 0, 1, 1])
        light = cols[..., :3] @ [0.299, 0.587, 0.114] > 0.5
        ink = np.empty((k, 6, 4))
        ink[..., :3] = np.where(light[..., None], rgb((20, 22, 32)), rgb(INK))
        ink[..., 3] = np.where(dim, 0.45, 0.95)[:, None]
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.icon_tex)
        draw_arrays(GL_QUADS, art, colors=np.repeat(ink[:, :, None], 4, axis=2), texcoords=uv)
        glDisable(GL_TEXTURE_2D)

        # white outlines
        glDisable(GL_LIGHTING)
        glLineWidth(1.2)
        edges = np.stack([quads, np.roll(quads, -1, axis=2)], axis=3)  # (k, 6, 4, 2, 3)
        ink = np.array(rgb(INK) + [0.0])
        ink_a = np.where(dim, 0.35, 0.85)
        line_cols = np.broadcast_to(ink, edges.shape[:-1] + (4,)).copy()
        line_cols[..., 3] = ink_a[:, None, None, None]
        draw_arrays(GL_LINES, edges, colors=line_cols)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)


# ----------------------------------------------------------------- 2D overlay
class Overlay:
    """Buttons and the solved flag, drawn with pygame (reusing rubik2d's
    widgets) onto a transparent surface shown as a texture over the GL frame."""

    def __init__(self, width, height):
        import pygame
        self.pg = pygame
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self.key = None

    def update(self, key, paint):
        """Repaint and re-upload only when `key` (what's on it) changes."""
        if key == self.key:
            return
        self.key = key
        self.surface.fill((0, 0, 0, 0))
        paint(self.surface)
        w, h = self.surface.get_size()
        data = self.pg.image.tobytes(self.surface, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

    def draw(self):
        w, h = self.surface.get_size()
        glViewport(0, 0, w, h)
        glDisable(GL_SCISSOR_TEST)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        for x, y in ((0, 0), (1, 0), (1, 1), (0, 1)):
            glTexCoord2f(x, y)
            glVertex2f(x, y)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glEnable(GL_FOG)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_SCISSOR_TEST)


# ----------------------------------------------------------------- galaxy buttons
def _lines(s, pts, closed=True, width=2, colour=INK):
    import pygame
    pygame.draw.lines(s, colour, closed, pts, width)
    pygame.draw.aalines(s, colour, closed, pts)


def _ellipse(c, rx, ry, tilt=0.0, n=48):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a = np.radians(tilt)
    x, y = rx * np.cos(t), ry * np.sin(t)
    return list(zip(c[0] + x * np.cos(a) - y * np.sin(a), c[1] + x * np.sin(a) + y * np.cos(a)))


def _ring(c, r, angles, scale=1.0):
    """Points at the given angles (degrees, counter-clockwise from +x)."""
    return [(c[0] + r * scale * np.cos(np.radians(a)), c[1] - r * scale * np.sin(np.radians(a)))
            for a in angles]


def draw_galaxy_icon(s, shape, c, r, width=2):
    """White line-art symbol of a galaxy's shape, centred on c, radius r."""
    import pygame
    line = lambda pts, closed=True: _lines(s, pts, closed, width)
    if shape == "cube":
        hexa = _ring(c, r, range(90, 450, 60))
        line(hexa)
        for p in (hexa[1], hexa[5], hexa[3]):  # the top-front corner's three edges
            line([c, p], False)
    elif shape == "tetrahedron":
        tri = _ring(c, r, (90, 210, 330))
        line(tri)
        mid = (c[0] + 0.12 * r, c[1] + 0.28 * r)
        for p in tri:
            line([mid, p], False)
    elif shape == "star":
        line([p for k in range(8) for p in _ring(c, r, [90 + 45 * k], 1 if k % 2 == 0 else 0.3)])
    elif shape == "octahedron":
        top, right, bottom, left = (c[0], c[1] - r), (c[0] + 0.75 * r, c[1]), (c[0], c[1] + r), \
            (c[0] - 0.75 * r, c[1])
        front = (c[0] + 0.15 * r, c[1] + 0.12 * r)
        line([top, right, bottom, left])
        line([left, front, right], False)
        line([top, front, bottom], False)
    elif shape == "dodecahedron":
        outer = _ring(c, r, range(90, 450, 36))
        inner = _ring(c, r, range(90, 450, 72), 0.52)
        line(outer)
        line(inner)
        for k, p in enumerate(inner):
            line([p, outer[2 * k]], False)
    elif shape == "torus":
        line(_ellipse(c, r, 0.62 * r))
        line(_ellipse((c[0], c[1] - 0.04 * r), 0.42 * r, 0.18 * r))
    else:  # ringed / double-ringed sphere
        pygame.draw.circle(s, INK, (int(c[0]), int(c[1])), int(0.55 * r), width)
        tilts = (-20,) if shape == "ringed sphere" else (28, -28)
        for t in tilts:
            line(_ellipse(c, r, 0.28 * r, t))


def draw_galaxy_button(s, rect, shape, focused, hover):
    """A dark tile with the galaxy's white symbol; the focused one is ringed."""
    import pygame
    if focused:
        pygame.draw.rect(s, INK, rect.inflate(10, 10), 3, border_radius=10)
    pygame.draw.rect(s, (34, 38, 76) if hover or focused else (14, 16, 36), rect, border_radius=7)
    pygame.draw.rect(s, INK if focused else RING_STYLE[1][0], rect, 2, border_radius=7)
    draw_galaxy_icon(s, shape, rect.center, rect.w * 0.32)


def draw_tooltip(s, rect, text, font, x):
    """The name of a hovered button, in a label level with it from x on."""
    import pygame
    if not font:
        return
    t = font.render(text, True, INK)
    box = t.get_rect().inflate(18, 10)
    box.midleft = (x, rect.centery)
    pygame.draw.rect(s, (16, 18, 42), box, border_radius=6)
    pygame.draw.rect(s, RING_STYLE[1][0], box, 1, border_radius=6)
    s.blit(t, t.get_rect(center=box.center))


# ----------------------------------------------------------------- app
class App:
    """Window, input, animation queue and the UI panel."""

    def __init__(self, width=1200, debug=False, hidden=False, scrambled=True, start=True,
                 solve=True):
        import pygame
        self.pg = pygame
        pygame.init()
        self.w, self.h = width, width // 2
        flags = pygame.OPENGL | pygame.DOUBLEBUF | (pygame.HIDDEN if hidden else 0)
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
            pygame.display.set_mode((self.w, self.h), flags)
        except pygame.error:  # no multisampling available
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
            pygame.display.set_mode((self.w, self.h), flags)
        pygame.display.set_caption("RASA Calibration Panel")
        self.font = load_font(max(16, self.h // 20))
        self.small = load_font(max(14, self.h // 30))
        self.show_help = self.show_solved = self.was_solved = False
        pad = self.pad = self.h // 40
        self.cells = focus_buttons(pygame, 2 * pad, pad, self.h // 11)
        panel = max(r.right for r in self.cells.values()) + pad
        self.debug = debug
        self.solve = debug and solve  # Space-solve (tesseract_helper turns it off)
        self.scene = Scene(self.w, self.h, show3d=debug, panel=panel)
        self.overlay = Overlay(self.w, self.h)
        self.sky, self.backdrop = Sky(self.w, self.h), Overlay(self.w, self.h)
        # start screen: one turn around the solved tesseract, until any key or click
        self.show_start = start
        self.start_frames = self.load_start_gif() if start else []
        self.tess = Tesseract()
        if scrambled:  # every game starts scrambled
            for name, q in scramble(rng=random.Random(SEED)):
                self.tess.apply(name, q)
        self.queue, self.anim = [], None

    def frame(self, t=None):
        """Advance the animation one step and draw everything (not flipped);
        `t` is the sky's clock in seconds (default: time since start)."""
        t = self.pg.time.get_ticks() / 1000 if t is None else t
        self.backdrop.update(t, lambda s: self.sky.draw(s, t))
        self.scene.time = t
        if self.anim is None and self.queue:
            name, q = self.queue.pop(0)
            steps = 5 if len(self.queue) > 3 else 16
            self.anim = [name, q, 0, steps * abs(q)]
        if self.anim:
            name, q, k, n = self.anim
            total = -90 * q
            self.scene.draw(self.tess, name, total * smooth(k / n), total, self.backdrop.draw)
            self.anim[2] += 1
            if self.anim[2] >= n:
                self.tess.apply(name, q)
                self.anim = None
        else:
            self.scene.draw(self.tess, backdrop=self.backdrop.draw)
        mouse = self.pg.mouse.get_pos()
        hover = [k for k, r in self.cells.items() if r.collidepoint(mouse)]
        solved = self.anim is None and not self.queue and self.tess.solved()
        if solved and not self.was_solved:  # just solved: show the flag
            self.show_solved, self.show_help = True, False
        self.was_solved = solved
        colours = tuple(self.tess.centre(c) for c in CELLS)
        still = self.start_frame(t) if self.show_start else None
        self.overlay.update((self.scene.focus, tuple(hover), colours, self.scene.show3d,
                             self.show_help, self.show_solved, still, self.scene.solo),
                            lambda s: self._paint(s, hover, still))
        self.overlay.draw()

    def _paint(self, s, hover, still=None):
        pg = self.pg
        for cell, rect in self.cells.items():  # each shows the galaxy centred there
            draw_galaxy_button(s, rect, SHAPE_OF_CELL[self.tess.centre(cell)],
                               cell == self.scene.focus, cell in hover)
        for cell in hover:
            if cell in self.cells:
                draw_tooltip(s, self.cells[cell], galaxy(SHAPE_OF_CELL[self.tess.centre(cell)]),
                             self.small, max(r.right for r in self.cells.values()) + 14)
        if self.scene.show3d:
            x = self.scene.debug.rect[0]
            pg.draw.line(s, RING_STYLE[1][0], (x, 0), (x, self.h), 2)
        if still is not None:
            draw_start(s, self.start_frames[still], max(14, self.h // 30), START_MESSAGE)
        elif self.show_solved:
            draw_solved(s, reveal_flag(self.tess), max(14, self.h // 24))
        elif self.show_help:
            draw_help(s, help_rows(self.debug, three_d=True, solve=self.solve), max(14, self.h // 30))
        elif self.scene.solo:
            draw_hint(s, self.small, f"Showing only the {galaxy(SHAPE_OF_CELL[self.tess.centre(self.scene.solo)])}"
                                     "  -  Ctrl+click it again to show all")
        else:
            draw_hint(s, self.small)

    def run(self):
        pg = self.pg
        clock = pg.time.Clock()
        keymap = {getattr(pg, f"K_{k.lower()}"): k for k in MOVES3}
        numbers = {getattr(pg, f"K_{k + 1}"): c for k, c in enumerate(CELLS)}
        press = None  # (view being dragged, pixels moved)
        running = True
        while running:
            for ev in pg.event.get():
                if ev.type == pg.QUIT:
                    running = False
                elif self.show_start:
                    if ev.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                        self.show_start = False  # (the press only closes the start screen)
                elif ev.type == pg.KEYDOWN:
                    if ev.key == pg.K_q:
                        running = False
                    elif ev.key == pg.K_ESCAPE:
                        if self.show_solved:
                            self.show_solved = False
                        else:
                            self.show_help = not self.show_help
                    elif self.show_help or self.show_solved:
                        pass  # those screens take no other keys
                    elif ev.key == pg.K_SPACE and self.solve:  # a fresh, solved tesseract
                        self.queue, self.anim = [], None
                        self.tess.reset()
                    elif ev.key == pg.K_TAB and self.debug:
                        self.scene.toggle_3d()
                    elif ev.key == pg.K_h:
                        self.scene.show_outer = not self.scene.show_outer
                    elif ev.key == pg.K_g:
                        self.scene.lattice_all = not self.scene.lattice_all
                    elif ev.key in numbers:
                        self.scene.focus = numbers[ev.key]
                    elif ev.key in keymap:
                        name = focus_move(self.scene.focus, keymap[ev.key],
                                          bool(ev.mod & pg.KMOD_CTRL))
                        self.queue.append((name, -1 if ev.mod & pg.KMOD_SHIFT else 1))
                elif ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
                    hit = [c for c, r in self.cells.items() if r.collidepoint(ev.pos)]
                    if self.show_help or self.show_solved:
                        self.show_help = self.show_solved = False
                    elif hit and pg.key.get_mods() & pg.KMOD_CTRL:
                        self.scene.set_solo(hit[0])
                    elif hit:
                        self.scene.focus = hit[0]
                    else:
                        press = [self.scene.view_at(ev.pos), 0]
                elif ev.type == pg.MOUSEMOTION and press:
                    press[0].orbit(*ev.rel)
                    press[1] += abs(ev.rel[0]) + abs(ev.rel[1])
                elif ev.type == pg.MOUSEBUTTONUP and ev.button == 1 and press:
                    if press[1] < 5:  # a click, not a drag: focus what's under it
                        cell = self.scene.pick(ev.pos)
                        if pg.key.get_mods() & pg.KMOD_CTRL and press[0] is self.scene.rings:
                            self.scene.set_solo(cell)  # (on nothing: show all again)
                        elif cell:
                            self.scene.focus = cell
                    press = None
                elif ev.type == pg.MOUSEWHEEL and not (self.show_help or self.show_solved):
                    self.scene.view_at(pg.mouse.get_pos()).zoom(1.1 ** ev.y)
            self.frame()
            pg.display.flip()
            clock.tick(60)
        pg.quit()

    START_FPS = 15  # with 180 frames: one slow turn every 12 s

    def start_frame(self, t):
        """Which GIF frame the start screen shows at time t."""
        return int(t * self.START_FPS) % len(self.start_frames)

    def load_start_gif(self, path=START_GIF):
        """The start screen's frames, recorded (see record_start_gif) if the
        file is missing."""
        from PIL import Image, ImageSequence
        if not os.path.exists(path):
            self.record_start_gif(path)
        return [surface_from_pil(f) for f in ImageSequence.Iterator(Image.open(path))]

    def record_start_gif(self, path=START_GIF, frames=180, size=400):
        """A GIF of one full turn of the camera around the solved tesseract
        (rings view, no cell highlighted, shapes not spinning so it loops; on
        the plain dark background, which keeps the file small)."""
        scene, view = self.scene, self.scene.rings
        saved = scene.show3d, view.yaw, view.dist, scene.highlight
        if scene.show3d:
            scene.toggle_3d()
        scene.highlight, scene.time = False, 0.0
        x, y, w, h = view.rect
        side = min(w, h)
        box = (x + (w - side) // 2, y + (h - side) // 2, x + (w + side) // 2, y + (h + side) // 2)
        images, solved = [], Tesseract()
        for i in range(frames):
            view.yaw = saved[1] + 2 * np.pi * i / frames
            scene.draw(solved)
            images.append(self.grab().crop(box).resize((size, size)))
        if saved[0]:
            scene.toggle_3d()
        view.yaw, view.dist, scene.highlight = saved[1], saved[2], saved[3]
        # one shared palette (from views all round, so every colour is in it)
        # and no dithering: smooth shading compresses far better
        from PIL import Image
        sample = images[::frames // 8]
        strip = Image.new("RGB", (size * len(sample), size))
        for k, im in enumerate(sample):
            strip.paste(im, (k * size, 0))
        palette = strip.quantize(colors=160, dither=Image.Dither.NONE)
        images = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        images[0].save(path, save_all=True, append_images=images[1:],
                       duration=1000 // self.START_FPS, loop=0)

    def grab(self):
        """The current frame as a PIL image."""
        from PIL import Image
        data = glReadPixels(0, 0, self.w, self.h, GL_RGB, GL_UNSIGNED_BYTE)
        img = np.frombuffer(data, dtype=np.uint8).reshape(self.h, self.w, 3)[::-1]
        return Image.fromarray(img)


def save_gif(seq, path, width=640, debug=False):
    app = App(width, debug=debug, hidden=True, scrambled=False, start=False)
    frames = []

    def shot(count=1):
        for _ in range(count):
            app.frame(len(frames) / 30)
            frames.append(app.grab())

    shot(10)
    for move in seq:
        app.queue.append(move)
        shot()
        while app.anim:
            shot()
        shot(3)
    shot(15)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0)
    print(f"saved {path} ({len(frames)} frames)")


# Public competitor build. When True, the hidden --debug flag (which enables the
# 4D debug view, Tab, and Space = instant solve) is not registered at all, so the
# shipped main binary cannot be coaxed into solving itself. The helper build
# (tesseract_helper.py) constructs App(debug=True, solve=False) directly and is
# unaffected by this switch. GM-only debug builds flip this to False and are
# never shipped in dist/.
PUBLIC_BUILD = True

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RASA calibration panel")
    ap.add_argument("moves", nargs="?", default="", help="e.g. \"RU FO' *RO 2UF\"")
    ap.add_argument("--gif", help="write an animated GIF instead of opening a window")
    ap.add_argument("--width", type=int, default=None)
    if not PUBLIC_BUILD:
        ap.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    debug = getattr(args, "debug", False)
    seq = parse(args.moves)
    if args.gif:
        save_gif(seq or scramble(12), args.gif, width=args.width or 640, debug=debug)
    else:
        app = App(args.width or 1200, debug=debug)
        app.queue = list(seq)
        app.run()
