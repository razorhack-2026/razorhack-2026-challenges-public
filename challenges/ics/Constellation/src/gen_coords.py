#!/usr/bin/env python3
"""
Challenge author tool: generate connect-the-dots coordinate data from flag text.
Outputs coordinates.json for the Modbus server, plus a preview image.

Usage: python src/gen_coords.py "flag{flag_here}"
"""

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

# DejaVu Sans (matplotlib's default) renders "fl" as a fused ligature glyph —
# a real problem here since every flag starts with "flag{". DejaVu Sans Mono
# (also bundled with matplotlib, no extra dependency) keeps every letter as
# its own separate outline.
FONT = FontProperties(family='DejaVu Sans Mono')


SCRIPT_DIR = Path(__file__).resolve().parent


def rdp_simplify(points: list[tuple], tolerance: float) -> list[tuple]:
    """Ramer-Douglas-Peucker polyline simplification."""
    if len(points) <= 2:
        return points

    pts = np.array(points)
    start, end = pts[0], pts[-1]
    d = end - start
    denom = np.dot(d, d) or 1.0
    t = np.clip(((pts - start) @ d) / denom, 0, 1)
    proj = start + np.outer(t, d)
    dists = np.linalg.norm(pts - proj, axis=1)

    idx = int(np.argmax(dists))
    if dists[idx] > tolerance:
        left = rdp_simplify(points[: idx + 1], tolerance)
        right = rdp_simplify(points[idx:], tolerance)
        return left[:-1] + right
    return [points[0], points[-1]]


def text_to_points(
    text: str,
    font_size: int = 100,
    output_scale: int = 10000,
    rdp_tolerance: int = 25,
) -> list[tuple[int, int, int]]:
    """
    Convert flag text to (x, y, pen) triplets.
    pen=0 means move to point without drawing; pen=1 means draw line from previous point.
    Coordinates are scaled to [0, output_scale].
    """
    tp = TextPath((0, 0), text, size=font_size, prop=FONT)
    polygons = tp.to_polygons()

    if not polygons:
        print("ERROR: No geometry generated — check that the flag text is non-empty.")
        sys.exit(1)

    all_pts = np.vstack(polygons)
    x_min, y_min = all_pts.min(axis=0)
    x_max, y_max = all_pts.max(axis=0)

    x_range = x_max - x_min or 1.0
    y_range = y_max - y_min or 1.0
    margin = output_scale * 0.05
    usable = output_scale - 2 * margin
    factor = usable / max(x_range, y_range)

    # Tolerance in original coordinate space
    tol = rdp_tolerance / factor

    points: list[tuple[int, int, int]] = []
    for poly in polygons:
        raw = [tuple(p) for p in poly]
        simplified = rdp_simplify(raw, tol)
        for i, (px, py) in enumerate(simplified):
            x = int((px - x_min) * factor + margin)
            y = int((py - y_min) * factor + margin)
            pen = 0 if i == 0 else 1
            points.append((x, y, pen))

    return points


def save_json(points: list[tuple[int, int, int]], path: str | Path = SCRIPT_DIR / 'coordinates.json') -> None:
    data = {
        'count': len(points),
        'points': [{'x': x, 'y': y, 'pen': pen} for x, y, pen in points],
    }
    with open(path, 'w') as f:
        json.dump(data, f)
    print(f"[+] Saved {len(points)} points -> {path}")


def save_preview(points: list[tuple[int, int, int]], path: str | Path = SCRIPT_DIR / 'preview.png') -> None:
    """Render a preview so the challenge author can verify the output looks correct."""
    fig, ax = plt.subplots(figsize=(14, 5), facecolor='#05050f')
    ax.set_facecolor('#05050f')
    ax.set_aspect('equal')
    ax.axis('off')

    prev: tuple[int, int] | None = None
    for x, y, pen in points:
        if pen == 1 and prev is not None:
            ax.plot([prev[0], x], [prev[1], y], color='#c8d8ff', lw=1.4, alpha=0.9)
        prev = (x, y)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.scatter(xs, ys, c='#00e5ff', s=5, zorder=5, alpha=0.75)

    plt.tight_layout(pad=0)
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#05050f')
    plt.close()
    print(f"[+] Preview saved  -> {path}")


if __name__ == '__main__':
    flag = sys.argv[1] if len(sys.argv) > 1 else 'flag{polaris_lock}'
    print(f"[*] Generating coordinates for: {flag!r}")
    pts = text_to_points(flag)
    save_json(pts)
    save_preview(pts)
    print(f"[*] Done. Register count: {1 + len(pts) * 3} holding registers total.")
