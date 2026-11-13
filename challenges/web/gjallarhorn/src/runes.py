"""Elder Futhark stroke templates + template-matching decoder. GM-only source.

Templates live in a unit box (x right, y UP). Each rune is a list of segments.
decode_points() recovers a rune from star positions alone (what a solver sees in graph.json).
"""
import math

RUNES = {  # letter -> (rune char, strokes)
    "O": ("ᛟ", [((.5, 1), (.9, .65)), ((.9, .65), (.5, .3)), ((.5, .3), (.1, .65)), ((.1, .65), (.5, 1)),
                ((.5, .3), (.1, 0)), ((.5, .3), (.9, 0))]),
    "D": ("ᛞ", [((.1, 0), (.1, 1)), ((.9, 0), (.9, 1)), ((.1, 0), (.9, 1)), ((.1, 1), (.9, 0))]),
    "N": ("ᚾ", [((.5, 0), (.5, 1)), ((.1, .65), (.9, .35))]),
    "R": ("ᚱ", [((.1, 0), (.1, 1)), ((.1, 1), (.75, .75)), ((.75, .75), (.1, .5)), ((.1, .5), (.75, 0))]),
    "A": ("ᚨ", [((.1, 0), (.1, 1)), ((.1, 1), (.7, .8)), ((.1, .7), (.7, .5))]),
    "G": ("ᚷ", [((.1, 0), (.9, 1)), ((.1, 1), (.9, 0))]),
    "K": ("ᚲ", [((.8, .85), (.2, .5)), ((.2, .5), (.8, .15))]),
}


def seg_len(s):
    return math.dist(s[0], s[1])


def sample_strokes(strokes, n):
    """n points spaced equally by arc length over all strokes (endpoints included)."""
    total = sum(seg_len(s) for s in strokes)
    pts = []
    for i in range(n):
        t = total * i / (n - 1)
        for s in strokes:
            L = seg_len(s)
            if t <= L + 1e-9:
                f = t / L if L else 0
                pts.append((s[0][0] + f * (s[1][0] - s[0][0]), s[0][1] + f * (s[1][1] - s[0][1])))
                break
            t -= L
    return pts


def _norm(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return [((x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)) for x, y in pts]


def _chamfer(a, b):
    d = lambda p, S: min(math.dist(p, q) for q in S)
    return sum(d(p, b) for p in a) / len(a) + sum(d(q, a) for q in b) / len(b)


_TPL = {k: _norm(sample_strokes(v[1], 60)) for k, v in RUNES.items()}


def decode_points(pts):
    """pts in math coords (y up). Returns (letter, score, margin_ratio best/second)."""
    P = _norm(pts)
    sc = sorted((_chamfer(P, T), k) for k, T in _TPL.items())
    return sc[0][1], sc[0][0], sc[1][0] / (sc[0][0] or 1e-9)


def layout(letter, cx, cy, h, n, rng, jitter=0.03, w_scale=0.8):
    """Screen-space points (y down) for n stars along the rune's strokes, upright."""
    # messy on purpose: stars drift off their even spacing along the strokes as well as sideways
    strokes = RUNES[letter][1]
    total = sum(seg_len(s) for s in strokes)
    base = sample_strokes(strokes, n)
    pts = []
    for i, p in enumerate(base):
        j = rng.uniform(-0.35, 0.35) * total / (n - 1)
        pts.append(sample_strokes(strokes, 400)[max(0, min(399, round((i * total / (n - 1) + j) / total * 399)))]
                   if 0 < i < n - 1 else p)
    out = []
    for x, y in pts:
        out.append((round(cx + (x - .5) * h * w_scale + rng.gauss(0, jitter * h), 1),
                    round(cy - (y - .5) * h + rng.gauss(0, jitter * h), 1)))
    return out


def bind_strokes(letters, cx, cy, h, w_scale=0.8, conjoin=True):
    """Bind-rune as screen-space segments. conjoin=True: one tall shared vertical stave; each rune
    is drawn on it, stacked top to bottom, centred on the stave (its own x=.5 axis), with a slight
    overlap between neighbours. A rune's own central stave (N) merges into the shared one.
    conjoin=False: plain side-by-side cells."""
    k = len(letters)
    if not conjoin:
        step = h * w_scale * 0.92
        segs = []
        for i, L in enumerate(letters):
            ox = cx + (i - (k - 1) / 2) * step
            for (a, b) in RUNES[L][1]:
                f = lambda p: [round(ox + (p[0] - .5) * h * w_scale, 1), round(cy - (p[1] - .5) * h, 1)]
                segs.append([f(a), f(b)])
        return segs
    ch = h / (k - (k - 1) * 0.12)          # cell height; neighbours overlap by 12%
    segs = [[[round(cx, 1), round(cy - h / 2, 1)], [round(cx, 1), round(cy + h / 2, 1)]]]
    for i, L in enumerate(letters):
        top = cy - h / 2 + i * ch * 0.88
        for (a, b) in RUNES[L][1]:
            if a[0] == b[0] == .5:
                continue                      # already the shared stave
            f = lambda p: [round(cx + (p[0] - .5) * ch * w_scale * 1.3, 1), round(top + (1 - p[1]) * ch, 1)]
            segs.append([f(a), f(b)])
    return segs


def decode_bind(segs, k, cx, cy, h, w_scale=0.8):
    """Split segments into k columns by x midpoint and decode each (densified)."""
    step = h * w_scale * 0.92
    cols = [[] for _ in range(k)]
    for a, b in segs:
        mx = (a[0] + b[0]) / 2
        i = min(range(k), key=lambda i: abs(mx - (cx + (i - (k - 1) / 2) * step)))
        cols[i].append(((a[0], -a[1]), (b[0], -b[1])))
    return [decode_points(sample_strokes(c, 60))[0] for c in cols]
