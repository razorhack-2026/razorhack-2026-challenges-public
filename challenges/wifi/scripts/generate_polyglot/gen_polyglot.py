#!/usr/bin/env python3
"""
gen_polyglot.py — build a PNG + PDF + ZIP polyglot for the `ODINS_EYES`
challenge: the carrier image renders normally, the PDF view prints the
(redacted) evil-twin hostapd config, and the ZIP view unpacks the two
competitor-facing challenge captures.

The single output file is simultaneously valid as three formats:

  * PNG  — readers parse from the 8-byte signature forward; our PDF header/body
           ride inside an ancillary chunk (safely ignored), and everything past
           the IEND chunk is ignored, so the carrier image renders unchanged.
  * PDF  — readers accept `%PDF-` anywhere in the first 1024 bytes and locate
           the trailer by scanning backward from EOF. We put `%PDF-` + the PDF
           objects in an early PNG chunk, and the xref/trailer/%%EOF after IEND
           (within the last 1024 bytes). PDF seeks to objects by absolute byte
           offset, so the intervening PNG image data is simply skipped over.
           The page draws the config text.
  * ZIP  — readers find the End-Of-Central-Directory record by scanning backward
           from EOF, so the archive appended last is well-formed. `unzip`/`7z`
           extract the bundled `.wav` captures out of the same bytes.

Byte layout of the output:

    [PNG signature]
    [IHDR chunk]
    [ancillary 'pdFz' chunk  -> "%PDF-1.7" + PDF objects (config text)]  <- first 1KB
    [IDAT ... IEND]                                          (carrier image data)
    [ZIP archive -> capture-01.wav, capture-02.wav]          <- EOCD near EOF
      \\__ ZIP end-of-central-directory COMMENT holds the PDF xref+trailer,
           so the PDF's %%EOF is the last bytes of the file (within last 1KB)
           while the ZIP stays well-formed (the trailer is just its comment).

Usage:
    python3 gen_polyglot.py [input.png] [output.png]
Defaults: input = satellite.png (beside this script), output = capture.png
"""

import argparse
import io
import os
import struct
import zipfile
import zlib

# --------------------------------------------------------------------------
# The evil-twin AP config (shape per solution/challenge8.md). Authored for this
# challenge; all sensitive values are blanked placeholders. This text is drawn
# onto the PDF page.
# --------------------------------------------------------------------------
HIDDEN_CONFIG = """\
YOU HAVE TO CLOSE MY EYES FIRST.
USE THIS TO TAKE CONTROL OF MY RAVENS AFTER.

# hostapd -B hostapd.conf
interface=wlan1
ssid=_________
hw_mode=a
channel=_________
country_code=US
ieee80211d=1
ieee80211w=2
wpa=2
auth_algs=1
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=_________
"""

# Files bundled into the ZIP view, relative to this script. These are the
# competitor-facing captures already shipped under dist/challenge8/.
DEFAULT_PAYLOAD = [
    "../generate_audio/capture-01.wav",
    "../generate_audio/capture-02.wav",
]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    """Serialize one PNG chunk: length | tag | data | CRC32(tag+data)."""
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def split_carrier_png(path: str):
    """Return (ihdr_chunk, rest) for a PNG, where rest is IDAT..IEND inclusive.

    The signature + IHDR stay up front (PNG demands them at offset 0); `rest`
    is everything from the first non-IHDR chunk through IEND. Any bytes after
    IEND in the source are dropped so our appended data is the only trailer.
    """
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path!r} is not a PNG (bad signature)")

    i = len(PNG_SIGNATURE)
    ihdr_chunk = None
    rest = bytearray()
    while i + 8 <= len(data):
        (length,) = struct.unpack(">I", data[i:i + 4])
        tag = data[i + 4:i + 8]
        end = i + 12 + length  # length(4) | tag(4) | data | crc(4)
        if end > len(data):
            raise ValueError(f"{path!r} is truncated inside chunk {tag!r}")
        chunk = data[i:end]
        if tag == b"IHDR":
            ihdr_chunk = chunk
        else:
            rest += chunk
        if tag == b"IEND":
            trailing = len(data) - end
            if trailing:
                print(f"[i] dropping {trailing} trailing byte(s) after IEND")
            break
        i = end

    if ihdr_chunk is None:
        raise ValueError(f"{path!r} has no IHDR chunk")
    if not rest.endswith(b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))):
        # IEND carries no data; its CRC is fixed. If it's missing, bail.
        if b"IEND" not in rest:
            raise ValueError(f"{path!r} has no IEND chunk")
    return ihdr_chunk, bytes(rest)


def build_pdf_objects(base_offset: int):
    """Build the early PDF bytes (header + objects) and their absolute offsets.

    `base_offset` is the absolute file offset at which these bytes will live.
    Returns (early_bytes, [abs offset of each 'N 0 obj']).
    """
    def esc(line: bytes) -> bytes:
        # Escape PDF string metacharacters: backslash, parentheses.
        return (line.replace(b"\\", b"\\\\")
                    .replace(b"(", b"\\(")
                    .replace(b")", b"\\)"))

    # Page content: a title line, a blank line, then each config line.
    lines = HIDDEN_CONFIG.encode("latin-1").split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()  # drop trailing empty line from the config's final newline

    # Multi-line text: set leading (TL), then emit each line with T* (next line).
    # Courier (monospace) keeps the config columns aligned.
    body = bytearray()
    body += b"BT\n/F1 12 Tf\n14 TL\n72 740 Td\n"
    for line in lines:
        body += b"(" + esc(line) + b") Tj T*\n"
    body += b"ET\n"
    stream = bytes(body)
    bodies = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]

    early = bytearray()
    early += b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"  # binary comment => treated as binary
    offsets = []
    for num, body in enumerate(bodies, start=1):
        offsets.append(base_offset + len(early))
        early += b"%d 0 obj\n" % num + body + b"\nendobj\n"
    return bytes(early), offsets


def build_pdf_trailer(xref_offset: int, obj_offsets) -> bytes:
    """Build the PDF xref table + trailer + startxref + %%EOF.

    Placed after IEND; `xref_offset` is where the `xref` keyword starts, and
    each 20-byte xref record points at an object's absolute file offset.
    """
    n = len(obj_offsets)
    out = bytearray()
    out += b"xref\n"
    out += b"0 %d\n" % (n + 1)
    out += b"0000000000 65535 f \n"            # object 0 (free), 20 bytes
    for off in obj_offsets:
        out += b"%010d 00000 n \n" % off        # 20 bytes each
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (n + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_offset
    return bytes(out)


def build_zip(file_paths, comment: bytes = b"") -> bytes:
    """Build a ZIP archive of the given files (stored by basename).

    `comment` becomes the archive's end-of-central-directory comment. We use it
    to carry the PDF trailer so the PDF's %%EOF ends up at the very end of the
    file while the ZIP remains valid (the trailer is a standard ZIP comment).
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in file_paths:
            zf.write(path, arcname=os.path.basename(path))
        if comment:
            zf.comment = comment
    return buf.getvalue()


def build_polyglot(ihdr_chunk: bytes, rest_png: bytes, payload_paths) -> bytes:
    """Assemble the PNG+PDF+ZIP polyglot bytes."""
    # The PDF chunk data begins right after: signature + IHDR + (len+type) of
    # the ancillary chunk. That fixed prefix length is the PDF's base offset.
    base = len(PNG_SIGNATURE) + len(ihdr_chunk) + 8
    early_pdf, obj_offsets = build_pdf_objects(base)

    # 'pdFz': ancillary (p) + private (d) + reserved-ok (F) + safe-to-copy (z).
    pdf_chunk = _png_chunk(b"pdFz", early_pdf)
    front = PNG_SIGNATURE + ihdr_chunk + pdf_chunk + rest_png

    # Build the ZIP once with no comment to learn its length. The PDF trailer
    # will be appended as the ZIP's EOCD comment, so the `xref` keyword lands
    # exactly at: len(front) + len(zip-without-comment).
    zip_no_comment = build_zip(payload_paths)
    xref_offset = len(front) + len(zip_no_comment)
    trailer = build_pdf_trailer(xref_offset, obj_offsets)

    # Rebuild the ZIP with the trailer as its comment (deterministic: identical
    # input => identical non-comment bytes, so the offset above still holds).
    zip_with_trailer = build_zip(payload_paths, comment=trailer)
    return front + zip_with_trailer


def verify(polyglot: bytes, expected_members) -> dict:
    """Structural self-checks for all three formats. Returns a small report."""
    report = {}

    # PNG: signature + walk to IEND.
    assert polyglot.startswith(PNG_SIGNATURE), "PNG signature missing"
    i = len(PNG_SIGNATURE)
    saw_iend = False
    while i + 8 <= len(polyglot):
        (length,) = struct.unpack(">I", polyglot[i:i + 4])
        tag = polyglot[i + 4:i + 8]
        if tag == b"IEND":
            saw_iend = True
            break
        i += 12 + length
    assert saw_iend, "PNG IEND not found"
    report["png"] = "signature + IHDR..IEND OK"

    # PDF: %PDF within first 1024 bytes, %%EOF within last 1024, startxref valid.
    head = polyglot[:1024]
    assert b"%PDF-" in head, "%PDF- not in first 1024 bytes"
    tail = polyglot[-1024:]
    assert b"%%EOF" in tail, "%%EOF not in last 1024 bytes"
    sx = polyglot.rfind(b"startxref")
    assert sx != -1, "startxref missing"
    xref_val = int(polyglot[sx:].split(b"\n")[1].strip())
    assert polyglot[xref_val:xref_val + 4] == b"xref", "startxref offset wrong"
    report["pdf"] = f"%PDF@{polyglot.find(b'%PDF-')} startxref->{xref_val} OK"

    # ZIP: opens, CRCs pass, expected members present.
    with zipfile.ZipFile(io.BytesIO(polyglot)) as zf:
        bad = zf.testzip()
        assert bad is None, f"ZIP member failed CRC: {bad}"
        names = zf.namelist()
    for want in expected_members:
        assert want in names, f"{want!r} not found in ZIP view"
    report["zip"] = f"members={names}"

    return report


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Build a PNG+PDF+ZIP polyglot: carrier image renders, PDF "
                    "shows the (redacted) ODINS_EYES config, ZIP unpacks the "
                    "challenge .wav captures."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=os.path.join(script_dir, "satellite.png"),
        help="carrier PNG (default: satellite.png beside this script)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="capture.png",
        help="output polyglot path (default: capture.png)",
    )
    parser.add_argument(
        "--payload",
        nargs="+",
        default=None,
        help="files to place in the ZIP view "
             "(default: the two dist/challenge8 .wav captures)",
    )
    args = parser.parse_args()

    raw_payload = args.payload if args.payload else DEFAULT_PAYLOAD
    payload = []
    for p in raw_payload:
        resolved = p if os.path.isabs(p) else os.path.normpath(
            os.path.join(script_dir, p))
        if not os.path.isfile(resolved):
            parser.error(f"payload file not found: {resolved}")
        payload.append(resolved)
    expected_members = [os.path.basename(p) for p in payload]

    ihdr_chunk, rest_png = split_carrier_png(args.input)
    polyglot = build_polyglot(ihdr_chunk, rest_png, payload)

    with open(args.output, "wb") as fh:
        fh.write(polyglot)

    report = verify(polyglot, expected_members)
    print(f"[+] wrote polyglot: {args.output} ({len(polyglot)} bytes)")
    print(f"    source : {args.input}")
    print(f"    PNG    : {report['png']}")
    print(f"    PDF    : {report['pdf']}")
    print(f"    ZIP    : {report['zip']}")
    print(f"    extract: unzip {args.output}  # -> {', '.join(expected_members)}")


if __name__ == "__main__":
    main()
