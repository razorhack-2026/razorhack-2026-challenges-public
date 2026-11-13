#!/usr/bin/env python3
"""Generate printable NFC share cards for "Are We There Yet?".

GM-ONLY. Reads ../shares.txt (the source of truth) and writes:

    share-01.pdf .. share-09.pdf   one wall card per share
    all-shares.pdf                 all nine cards, one per page
    nfc_payloads.txt               exact text to write to each NFC tag
    nfc_payloads.csv               same data + suggested placement

By default the share VALUE is not printed on the card - it lives only on the
NFC tag. Pass --include-value to also print a paper fallback (use this only if
you are worried about tag failures; it makes the tag optional).

No third-party dependencies: this writes the PDF directly.

Usage:
    python3 make_share_cards.py [--include-value] [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

PAGE_W, PAGE_H = 612.0, 792.0          # US Letter, points
M = 36.0                                # page margin

NAVY = (0.055, 0.130, 0.240)
CYAN = (0.000, 0.550, 0.650)
AMBER = (0.800, 0.520, 0.100)
GRAY = (0.420, 0.420, 0.420)
MIDGRAY = (0.700, 0.740, 0.780)
LIGHT = (0.945, 0.965, 0.975)
WHITE = (1.0, 1.0, 1.0)
BLACK = (0.05, 0.05, 0.05)
RED = (0.640, 0.120, 0.120)

# Approximate advance widths (fraction of point size). Good enough for
# centering short labels; all body text is left-aligned.
WIDTH_FACTOR = {"F1": 0.552, "F2": 0.580, "F3": 0.600, "F4": 0.552, "F5": 0.600}

FLAVOR = {
    1: "The first fragment. The archive does not say who pulled it.",
    2: 'Filed under "do not lose this". The filing was ignored.',
    3: "A fragment of the key, sealed inside a shipping envelope.",
    4: "Recovered from a routine audit that was anything but routine.",
    5: 'The archive lists this fragment as "probably fine".',
    6: "Pulled from the drift telemetry before the buffer rotated.",
    7: "One of the nine. Alone, it is just noise.",
    8: "Logged, stamped, and then immediately misplaced.",
    9: "The last fragment on the manifest. Or the first, depending on the manifest.",
}

# Shares that already have a delivery location in solution/solution.md. These
# are handed out by crew / placed on materials, so they do NOT get a wall card.
PLACEMENT = {
    2: "crew - Lt. Rico Kopernicus",
    4: "material - flyer",
    5: "material - website",
    9: "crew - Davie Bowman",
}


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def rgb(color) -> str:
    return " ".join(num(c) for c in color)


def text_width(text: str, font: str, size: float) -> float:
    return len(text) * WIDTH_FACTOR[font] * size


class Canvas:
    """Collects PDF content-stream operators."""
    def __init__(self) -> None:
        self.ops: list[str] = []

    def raw(self, op: str) -> None:
        self.ops.append(op)

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1.0, dash=None):
        if fill:
            self.raw(f"{rgb(fill)} rg")
        if stroke:
            self.raw(f"{rgb(stroke)} RG {num(lw)} w")
        if dash:
            self.raw(f"[{dash}] 0 d")
        self.raw(f"{num(x)} {num(y)} {num(w)} {num(h)} re")
        if fill and stroke:
            self.raw("B")
        elif fill:
            self.raw("f")
        else:
            self.raw("S")
        if dash:
            self.raw("[] 0 d")

    def line(self, x1, y1, x2, y2, color=BLACK, lw=1.0, dash=None):
        if dash:
            self.raw(f"[{dash}] 0 d")
        self.raw(f"{rgb(color)} RG {num(lw)} w")
        self.raw(f"{num(x1)} {num(y1)} m {num(x2)} {num(y2)} l S")
        if dash:
            self.raw("[] 0 d")

    def circle(self, cx, cy, r, fill=None, stroke=None, lw=1.0, dash=None):
        k = 0.5522847498307936 * r
        if fill:
            self.raw(f"{rgb(fill)} rg")
        if stroke:
            self.raw(f"{rgb(stroke)} RG {num(lw)} w")
        if dash:
            self.raw(f"[{dash}] 0 d")
        self.raw(
            f"{num(cx + r)} {num(cy)} m "
            f"{num(cx + r)} {num(cy + k)} {num(cx + k)} {num(cy + r)} {num(cx)} {num(cy + r)} c "
            f"{num(cx - k)} {num(cy + r)} {num(cx - r)} {num(cy + k)} {num(cx - r)} {num(cy)} c "
            f"{num(cx - r)} {num(cy - k)} {num(cx - k)} {num(cy - r)} {num(cx)} {num(cy - r)} c "
            f"{num(cx + k)} {num(cy - r)} {num(cx + r)} {num(cy - k)} {num(cx + r)} {num(cy)} c"
        )
        self.raw("B" if (fill and stroke) else ("f" if fill else "S"))
        if dash:
            self.raw("[] 0 d")

    def arc(self, cx, cy, r, a0, a1, color=NAVY, lw=3.0):
        """Arc from a0 to a1 degrees (0 = +x, CCW), split into <=90 segments."""
        self.raw(f"{rgb(color)} RG {num(lw)} w")
        start = True
        a = a0
        while a < a1:
            b = min(a + 90.0, a1)
            rad_a, rad_b = math.radians(a), math.radians(b)
            delta = rad_b - rad_a
            k = 4.0 / 3.0 * math.tan(delta / 4.0) * r
            p0 = (cx + r * math.cos(rad_a), cy + r * math.sin(rad_a))
            p3 = (cx + r * math.cos(rad_b), cy + r * math.sin(rad_b))
            p1 = (p0[0] - k * math.sin(rad_a), p0[1] + k * math.cos(rad_a))
            p2 = (p3[0] + k * math.sin(rad_b), p3[1] - k * math.cos(rad_b))
            self.raw(f"{num(p0[0])} {num(p0[1])} {'m' if start else 'l'}")
            self.raw(
                f"{num(p1[0])} {num(p1[1])} {num(p2[0])} {num(p2[1])} "
                f"{num(p3[0])} {num(p3[1])} c"
            )
            start = False
            a = b
        self.raw("S")

    def nfc_icon(self, cx, cy, size=40.0):
        """Dot + three arcs opening to the right (NFC-ish mark)."""
        dot_x = cx - size * 0.35
        self.circle(dot_x, cy, max(2.2, size * 0.07), fill=NAVY)
        for factor in (0.36, 0.66, 0.96):
            self.arc(dot_x, cy, size * factor, -52, 52, NAVY, 2.6)

    def text(self, x, y, text, font="F1", size=10, color=BLACK):
        self.raw(f"{rgb(color)} rg")
        self.raw(f"BT /{font} {num(size)} Tf {num(x)} {num(y)} Td ({esc(text)}) Tj ET")

    def center(self, cx, y, text, font="F1", size=10, color=BLACK):
        self.text(cx - text_width(text, font, size) / 2.0, y, text, font, size, color)


class PDFWriter:
    def __init__(self) -> None:
        self.objs: list = [None]

    def add(self, body: bytes) -> int:
        self.objs.append(body)
        return len(self.objs) - 1

    def set(self, obj_id: int, body: bytes) -> None:
        self.objs[obj_id] = body

    def save(self, path: Path, root_id: int) -> None:
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * len(self.objs)
        for obj_id in range(1, len(self.objs)):
            offsets[obj_id] = len(out)
            out += f"{obj_id} 0 obj\n".encode("ascii")
            out += self.objs[obj_id] or b""
            out += b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(self.objs)}\n".encode("ascii")
        out += b"0000000000 65535 f \n"
        for obj_id in range(1, len(self.objs)):
            out += f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii")
        out += (
            f"trailer\n<< /Size {len(self.objs)} /Root {root_id} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
        path.write_bytes(out)


def build_pdf(pages, path: Path) -> None:
    writer = PDFWriter()
    catalog = writer.add(b"")
    pages_id = writer.add(b"")
    fonts = {}
    for key, base in (
        ("F1", "Helvetica"),
        ("F2", "Helvetica-Bold"),
        ("F3", "Courier"),
        ("F4", "Helvetica-Oblique"),
        ("F5", "Courier-Bold"),
    ):
        body = (
            "<< /Type /Font /Subtype /Type1 /BaseFont /"
            + base
            + " /Encoding /WinAnsiEncoding >>"
        )
        fonts[key] = writer.add(body.encode("ascii"))
    kid_refs = []
    font_res = " ".join("/%s %d 0 R" % (key, obj) for key, obj in fonts.items())
    for canvas in pages:
        data = "\n".join(canvas.ops).encode("latin-1")
        content = writer.add(
            ("<< /Length %d >>\nstream\n" % len(data)).encode("ascii")
            + data
            + b"\nendstream"
        )
        page_body = (
            "<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %s %s] "
            "/Resources << /Font << %s >> >> /Contents %d 0 R >>"
            % (pages_id, num(PAGE_W), num(PAGE_H), font_res, content)
        )
        kid_refs.append("%d 0 R" % writer.add(page_body.encode("ascii")))
    kids = " ".join(kid_refs)
    writer.set(
        pages_id,
        ("<< /Type /Pages /Count %d /Kids [%s] >>" % (len(kid_refs), kids)).encode(
            "ascii"
        ),
    )
    writer.set(catalog, ("<< /Type /Catalog /Pages %d 0 R >>" % pages_id).encode("ascii"))
    writer.save(path, catalog)


def share_card(index, total, modulus, threshold, include_value, value=""):
    c = Canvas()
    top = PAGE_H

    # Top band and masthead.
    c.rect(0, top - 18, PAGE_W, 18, fill=NAVY)
    c.text(M, top - 13, "RAZERPOWERCO", "F2", 10, WHITE)
    c.text(PAGE_W - M - 118, top - 12.5, "NAV-FORM 09 / KEY RECOVERY", "F1", 7, (0.75, 0.82, 0.90))
    c.text(M, top - 40, "SHIPBOARD NAVIGATION INTEGRITY PROGRAM", "F2", 8, GRAY)
    c.line(M, top - 46, PAGE_W - M, top - 46, CYAN, 1.2)

    # Title block.
    c.text(M, top - 84, "ARE WE THERE YET?", "F2", 26, NAVY)
    c.text(M, top - 104, "PHYSICAL NAVIGATION KEY SHARE", "F2", 10, CYAN)
    c.rect(PAGE_W - M - 96, top - 112, 96, 42, stroke=AMBER, lw=1.2)
    c.center(PAGE_W - M - 48, top - 89, "ONE OF NINE", "F2", 8, AMBER)
    c.center(PAGE_W - M - 48, top - 103, "DO NOT REMOVE", "F1", 6.5, GRAY)

    # Main card.
    card_y0, card_h = top - 330, 200
    c.rect(M, card_y0, PAGE_W - 2 * M, card_h, fill=LIGHT, stroke=NAVY, lw=1.6)
    left_w = (PAGE_W - 2 * M) * 0.42
    c.text(M + 22, card_y0 + card_h - 28, "SHARE", "F2", 11, GRAY)
    digits = "%02d" % index
    c.text(M + 22, card_y0 + 70, digits, "F2", 92, NAVY)
    c.text(M + 32 + text_width(digits, "F2", 92), card_y0 + 74, "/ %02d" % total, "F2", 18, CYAN)
    c.text(M + 22, card_y0 + 22, "RECORD THIS SHARE.", "F2", 8, GRAY)
    c.line(M + left_w, card_y0 + 18, M + left_w, card_y0 + card_h - 18, MIDGRAY, 0.8)

    # NFC tap target.
    cx = M + left_w + (PAGE_W - 2 * M - left_w) / 2.0
    cy = card_y0 + 112
    radius = 54
    c.circle(cx, cy, radius, stroke=MIDGRAY, lw=1.2, dash="5 4")
    c.nfc_icon(cx - 4, cy, 44)
    c.center(cx, cy - radius - 12, "TAP PHONE HERE", "F2", 9, NAVY)
    c.center(cx, cy - radius - 24, "Hold the top of your phone against the tag.", "F1", 7.5, GRAY)

    # Instructions.
    iy0, ih = top - 500, 150
    c.rect(M, iy0, PAGE_W - 2 * M, ih, stroke=MIDGRAY, lw=0.9)
    c.rect(M, iy0 + ih - 24, PAGE_W - 2 * M, 24, fill=(0.90, 0.93, 0.96))
    c.text(M + 14, iy0 + ih - 16, "HOW TO READ THIS SHARE", "F2", 10, NAVY)
    lines = [
        "1. Turn on NFC, then hold the TOP of your phone against the dashed circle above.",
        "2. The tag returns one line: a share index, a comma, and a 0x-prefixed hex value.",
        "3. Keep it exactly as written. Field 1 is x; field 2 is the share value y.",
        "4. Nine shares exist; any FIVE distinct shares are enough to rebuild the key.",
        "5. Leave this card mounted. If reaching it needs tools, it is not a share.",
    ]
    y = iy0 + ih - 48
    for line in lines:
        c.text(M + 14, y, line, "F1", 9, BLACK)
        y -= 16

    # Data box.
    dy0, dh = top - 580, 68
    c.rect(M, dy0, PAGE_W - 2 * M, dh, fill=LIGHT)
    c.text(M + 14, dy0 + dh - 18, "NAVIGATION MODULUS (PUBLIC)", "F2", 9, GRAY)
    c.text(M + 14, dy0 + dh - 34, modulus, "F3", 7.5, BLACK)
    if include_value:
        c.text(M + 14, dy0 + dh - 52, "SHARE VALUE (PAPER FALLBACK): " + value, "F3", 7.5, RED)
    else:
        c.text(
            M + 14,
            dy0 + dh - 52,
            "No key material is printed on this card. The share exists only on the NFC tag.",
            "F1",
            8,
            GRAY,
        )

    # Flavor + footer.
    c.text(M, 186, FLAVOR.get(index, ""), "F4", 9.5, GRAY)
    c.line(M, 168, PAGE_W - M, 168, MIDGRAY, 0.8)
    c.text(M, 148, "SERIAL RPC-NAV-SHR-%04d" % index, "F5", 8, NAVY)
    c.text(M, 134, "PROPERTY OF RAZERPOWERCO - NAVIGATION INTEGRITY PROGRAM", "F1", 6.5, GRAY)
    c.text(M, 123, "Physical challenge prop. Do not dismantle, relocate, or remove the tag.", "F1", 6.5, GRAY)

    # Decorative barcode, unique per card.
    bx, by = PAGE_W - M - 150, 100
    seed = index * 2654435761 & 0xFFFFFFFF
    for col in range(48):
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        width = 0.8 + ((seed >> 28) % 3) * 0.6
        height = 14 + ((seed >> 20) & 0x1F)
        if col % 2 == 0:
            c.rect(bx + col * 3.05, by, width, height, fill=NAVY)
    c.text(bx, 84, "09-%02d-RPC" % index, "F3", 6.5, GRAY)

    # Bottom band.
    c.rect(0, 0, PAGE_W, 12, fill=NAVY)
    c.center(PAGE_W / 2, 4, "RAZERPOWERCO // LOST IN SPACE // RAZORHACK 2026", "F1", 5.5, (0.80, 0.87, 0.95))
    return c


def load_shares(path: Path):
    threshold = None
    modulus = None
    shares = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"#\s*Threshold:\s*(\d+)", line, re.I)
        if match:
            threshold = int(match.group(1))
            continue
        match = re.match(r"#\s*Modulus:\s*(0x[0-9a-fA-F]+)", line, re.I)
        if match:
            modulus = match.group(1)
            continue
        if line.startswith("#"):
            continue
        x_part, y_part = line.split(",", 1)
        shares.append((int(x_part.strip()), y_part.strip()))
    if not shares or threshold is None or modulus is None:
        raise SystemExit("could not parse shares, threshold, or modulus from %s" % path)
    return threshold, modulus, shares


def write_payloads(out_dir: Path, shares, threshold, modulus):
    txt = [
        "# Are We There Yet? - NFC tag payloads (GM-ONLY)",
        "#",
        "# Write the payload for each share as a single NDEF TEXT record.",
        "# Keep it exactly as written: <share index>, <0x-prefixed value>.",
        "# Field 1 is the evaluation point x; field 2 is the share value y.",
        "#",
        "# Threshold: %d of %d shares" % (threshold, len(shares)),
        "# Modulus: %s" % modulus,
        "#",
        "# These files must never be shipped to players or copied into dist/.",
        "",
    ]
    for index, value in shares:
        txt.append("%d, %s" % (index, value))
    (out_dir / "nfc_payloads.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")

    with (out_dir / "nfc_payloads.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = csv.writer(handle)
        rows.writerow(["share", "payload", "threshold", "modulus", "suggested_placement"])
        for index, value in shares:
            rows.writerow(
                [index, "%d, %s" % (index, value), threshold, modulus, PLACEMENT.get(index, "wall")]
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-value",
        action="store_true",
        help="also print the share value on the card (paper fallback if NFC fails)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="output directory (default: this script's directory)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="also generate cards for shares that already have a crew/material location",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    shares_file = here.parent / "shares.txt"
    threshold, modulus, shares = load_shares(shares_file)
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(shares)
    if args.all or not PLACEMENT:
        selected = shares
    else:
        selected = [(index, value) for index, value in shares if index not in PLACEMENT]

    # Drop cards from a previous run so stale PDFs do not linger when the
    # selection changes (e.g. going from nine cards to the five wall shares).
    for stale in list(out_dir.glob("share-*.pdf")) + list(out_dir.glob("all-shares.pdf")):
        stale.unlink()

    pages = []
    for index, value in selected:
        canvas = share_card(index, total, modulus, threshold, args.include_value, value)
        pages.append(canvas)
        build_pdf([canvas], out_dir / ("share-%02d.pdf" % index))
    build_pdf(pages, out_dir / "all-shares.pdf")
    write_payloads(out_dir, shares, threshold, modulus)

    print(
        "Wrote %d card(s), all-shares.pdf, and payload sheets for all %d shares to %s"
        % (len(pages), total, out_dir)
    )
    print("Wall shares: %s" % ", ".join(str(i) for i, _ in selected))
    print("Threshold %d of %d, modulus %s" % (threshold, total, modulus))


if __name__ == "__main__":
    main()
