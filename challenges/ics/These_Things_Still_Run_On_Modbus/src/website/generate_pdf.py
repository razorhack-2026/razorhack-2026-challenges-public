"""Generates the DM-7 Operations Manual PDF at build time."""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = "/output/DM-7_Operations_Manual_v2.3.pdf"

# Same VENDOR_URL convention as src/drone/server.py — where the website
# itself is actually reachable from a participant. Set at image build
# time (see Dockerfile ARG), since this PDF is baked in at build.
VENDOR_URL = os.environ.get("VENDOR_URL", "http://localhost:8080")

W, H = A4
DARK  = colors.HexColor("#0a0e1a")
TEAL  = colors.HexColor("#00d4ff")
GREY  = colors.HexColor("#c8cdd8")
RED   = colors.HexColor("#ff4444")

base   = getSampleStyleSheet()

cover_title = ParagraphStyle("cover_title",
    parent=base["Title"], fontSize=28, textColor=TEAL,
    alignment=TA_CENTER, spaceAfter=12)

cover_sub = ParagraphStyle("cover_sub",
    parent=base["Normal"], fontSize=13, textColor=GREY,
    alignment=TA_CENTER, spaceAfter=6)

h1 = ParagraphStyle("h1",
    parent=base["Heading1"], fontSize=16, textColor=TEAL,
    spaceBefore=18, spaceAfter=6)

h2 = ParagraphStyle("h2",
    parent=base["Heading2"], fontSize=12, textColor=TEAL,
    spaceBefore=12, spaceAfter=4)

body = ParagraphStyle("body",
    parent=base["Normal"], fontSize=10, textColor=colors.black,
    leading=15, spaceAfter=8)

warn = ParagraphStyle("warn",
    parent=base["Normal"], fontSize=10, textColor=RED,
    leading=15, spaceAfter=8, borderPad=6)

mono = ParagraphStyle("mono",
    parent=base["Code"], fontSize=10, textColor=colors.black,
    backColor=colors.HexColor("#e8e8e8"), leading=14,
    leftIndent=12, spaceAfter=8)

toc_entry = ParagraphStyle("toc_entry",
    parent=base["Normal"], fontSize=10, textColor=colors.black,
    leading=16)

cell = ParagraphStyle("cell",
    parent=base["Normal"], fontSize=9, textColor=colors.black, leading=12)

cell_header = ParagraphStyle("cell_header",
    parent=base["Normal"], fontSize=9, textColor=colors.white,
    leading=12, fontName="Helvetica-Bold")


def hr():
    return HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=8, spaceBefore=4)


def wrapped_table(rows, col_widths):
    """Build a Table whose cells are Paragraphs, so long content wraps inside
    its column instead of overflowing past the page margin. First row is
    treated as the header."""
    data = [[Paragraph(str(c), cell_header) for c in rows[0]]] + [
        [Paragraph(str(c), cell) for c in row] for row in rows[1:]
    ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title="AstraTech DM-7 Mining Drone — Operations Manual v2.3",
        author="AstraTech Industries Technical Documentation Team",
    )

    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 3*cm),
        Paragraph("ASTRATECH INDUSTRIES", cover_sub),
        Paragraph("DM-7 Mining Drone", cover_title),
        Paragraph("Operations Manual", cover_title),
        Spacer(1, 0.5*cm),
        Paragraph("Revision 2.3.1  •  Firmware v2.3.1  •  CONFIDENTIAL", cover_sub),
        Spacer(1, 0.5*cm),
        hr(),
        Spacer(1, 0.4*cm),
        Paragraph(
            "This document contains proprietary information of AstraTech Industries. "
            "Unauthorised reproduction or distribution is strictly prohibited. "
            f"For support, visit <b>{VENDOR_URL}</b>.",
            cover_sub,
        ),
        PageBreak(),
    ]

    # ── Table of Contents ────────────────────────────────────────────────────
    story += [
        Paragraph("Table of Contents", h1),
        hr(),
        Spacer(1, 0.3*cm),
    ]
    toc = [
        ("1.", "Introduction & Safety"),
        ("2.", "Technical Specifications"),
        ("3.", "Pre-Deployment Checklist"),
        ("4.", "Mining Operations"),
        ("5.", "Telemetry & Monitoring"),
        ("6.", "Fault Diagnosis"),
        ("7.", "Firmware Updates"),
        ("8.", "Maintenance Schedule"),
        ("9.", "Emergency Protocols"),
        ("A.", "Appendix A — Modbus Register Map"),
    ]
    for num, title in toc:
        story.append(Paragraph(f"&nbsp;&nbsp;{num}&nbsp;&nbsp;&nbsp;{title}", toc_entry))
    story.append(PageBreak())

    # ── Section 1 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 1 — Introduction & Safety", h1), hr(),
        Paragraph(
            "The AstraTech DM-7 is a fully autonomous mineral-extraction drone designed for "
            "deployment in low-gravity asteroid belt environments. Building on the proven DM-5 "
            "platform, the DM-7 introduces dual-axis laser drilling, an onboard ore assay unit, "
            "and a redundant Modbus TCP control interface rated for deep-space latency.",
            body),
        Paragraph("Safety Notices", h2),
        Paragraph(
            "<b>WARNING:</b> The DM-7 operates laser arrays rated at 12 kW. Ensure all personnel "
            "maintain a minimum exclusion radius of 400 m during active drilling.",
            warn),
        Paragraph(
            "<b>CAUTION:</b> The emergency destruct system (Section 9) is irreversible. "
            "Confirm operator authorisation before executing.",
            warn),
        PageBreak(),
    ]

    # ── Section 2 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 2 — Technical Specifications", h1), hr(),
    ]
    specs = [
        ["Parameter", "Value"],
        ["Dimensions (stowed)", "1.4 m × 1.4 m × 0.6 m"],
        ["Mass (dry)", "312 kg"],
        ["Power source", "RTG + solar array, 4.2 kW continuous"],
        ["Max drilling depth", "18 m"],
        ["Drill laser output", "12 kW (pulsed)"],
        ["Ore hopper capacity", "850 kg"],
        ["Comms interface", "Modbus TCP/IP — port 502"],
        ["Modbus unit identifier", "0x0A (decimal 10)"],
        ["Supported function codes", "FC01, FC02, FC03, FC04, FC06, FC16, FC43"],
        ["Operating temp range", "−120 °C to +180 °C"],
        ["Firmware revision", "v2.3.1"],
    ]
    t = wrapped_table(specs, col_widths=[6*cm, 10*cm])
    story += [t, PageBreak()]

    # ── Section 3 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 3 — Pre-Deployment Checklist", h1), hr(),
        Paragraph(
            "Before releasing the DM-7 from the carrier bay, verify the following via the "
            "Modbus holding-register interface (FC03):",
            body),
        Paragraph("• Register 0x0002 (battery_percent) ≥ 0x0050 (80 %)", body),
        Paragraph("• Register 0x0005 (fault_flags) == 0x0000", body),
        Paragraph("• Register 0x0003 (operational_status) == 0x0001 (TRANSIT)", body),
        Paragraph(
            "If any check fails, do not proceed. Consult Section 6 (Fault Diagnosis).",
            body),
        PageBreak(),
    ]

    # ── Section 4 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 4 — Mining Operations", h1), hr(),
        Paragraph(
            "Once on-site, the DM-7 transitions automatically to DRILL (0x0002) then MINING "
            "(0x0003) status. Monitor telemetry registers continuously:",
            body),
        Paragraph("• ore_density_kg_m3 (register 0x0000) — target ≥ 0x0032 (50 kg/m³)", body),
        Paragraph("• thruster_temp_celsius (register 0x0001) — alarm threshold 0x02BC (700 °C)", body),
        Paragraph("• battery_percent (register 0x0002) — initiate RTB below 0x0014 (20 %)", body),
        PageBreak(),
    ]

    # ── Section 5 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 5 — Telemetry & Monitoring", h1), hr(),
        Paragraph(
            "All telemetry is exposed as read-only Modbus holding registers accessible via FC03 "
            "on unit identifier 0x0A.  Poll at intervals no shorter than 250 ms to avoid "
            "saturating the control link.",
            body),
        Paragraph(
            "Device identification (FC43, MEI type 0x0E) returns the vendor name, product code, "
            "firmware revision, and vendor support URL.  No authentication is required for FC43.",
            body),
        PageBreak(),
    ]

    # ── Section 6 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 6 — Fault Diagnosis", h1), hr(),
        Paragraph(
            "Register 0x0005 (fault_flags) is a bitmask.  Decode individual bits as follows:",
            body),
    ]
    faults = [
        ["Bit", "Fault", "Action"],
        ["0",  "Thruster overtemp",   "Reduce thrust, monitor register 0x0001"],
        ["1",  "Battery low",          "Initiate RTB immediately"],
        ["2",  "Drill jam",            "Retract and re-position"],
        ["3",  "Comms watchdog",       "Re-establish Modbus link"],
        ["4",  "Hopper full",          "Return to base for unload"],
        ["5–15", "Reserved",           "—"],
    ]
    ft = wrapped_table(faults, col_widths=[1.6*cm, 6.2*cm, 8.2*cm])
    story += [ft, PageBreak()]

    # ── Section 7 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 7 — Firmware Updates", h1), hr(),
        Paragraph(
            "Firmware updates are delivered over the Modbus TCP link using a proprietary "
            "multi-write sequence (FC16).  Contact AstraTech support for update packages.  "
            "The current firmware revision is reported via FC43 object 0x02 (MajorMinorRevision).",
            body),
        PageBreak(),
    ]

    # ── Section 8 ────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 8 — Maintenance Schedule", h1), hr(),
        Paragraph(
            "Perform the following maintenance at the indicated intervals:",
            body),
        Paragraph("• Every 500 operational hours — inspect drill head and replace laser emitters", body),
        Paragraph("• Every 1000 hours — full thruster overhaul", body),
        Paragraph("• Every 2000 hours — RTG shielding inspection (qualified personnel only)", body),
        PageBreak(),
    ]

    # ── Section 9 — KEY SECTION ───────────────────────────────────────────────
    story += [
        Paragraph("Section 9 — Emergency Protocols", h1), hr(),
        Paragraph("9.1  Emergency Return-to-Base (ERtB)", h2),
        Paragraph(
            "Write 0x0004 to register 0x0003 (operational_status) to force immediate RTB "
            "regardless of current mission state.",
            body),
        Paragraph("9.2  Emergency Destruct Protocol (EDP)", h2),
        Paragraph(
            "In the event of unrecoverable drone compromise — including hostile capture, "
            "uncontrolled trajectory, or irreversible software fault — authorised operators "
            "may initiate the Emergency Destruct Protocol.  <b>This action is irreversible.</b>",
            body),
        Paragraph(
            "<b>WARNING:</b> EDP triggers a cascading RTG containment failure and "
            "complete structural disintegration within 30 seconds.  Ensure all personnel "
            "and assets are outside a 2 km radius before issuing the command.",
            warn),
        Paragraph("EDP Procedure", h2),
        Paragraph("1.  Establish a Modbus TCP connection to the drone on port 502.", body),
        Paragraph("2.  Set the client unit identifier to <b>0x0A</b>.", body),
        Paragraph("3.  Write the Authorization Code to the designated destruct register:", body),
        Paragraph(
            "    Authorization Code :  0x4444\n"
            "    Target Register    :  1337  (0x0539)\n"
            "    Unit Identifier    :  0x0A",
            mono),
        Paragraph(
            "4.  The drone will acknowledge receipt.  "
            "Destruct confirmation data will be available in holding registers "
            "2000–2017 (0x07D0–0x07E1) immediately after the write is accepted.",
            body),
        Paragraph(
            "5.  Read registers 2000–2017 to retrieve the destruct confirmation token.",
            body),
        Paragraph(
            "<b>Note:</b> Requests issued with any unit identifier other than 0x0A will be "
            "silently discarded by the drone's Modbus stack.",
            warn),
        PageBreak(),
    ]

    # ── Appendix A — Register Map ────────────────────────────────────────────
    story += [
        Paragraph("Appendix A — Modbus Holding Register Map", h1), hr(),
        Paragraph("All registers are 16-bit unsigned integers.  Access via FC03 (read) / FC06 (write single) / FC16 (write multiple).", body),
    ]
    regs = [
        ["Address (dec)", "Address (hex)", "Name",                   "R/W", "Notes"],
        ["0",    "0x0000", "ore_density_kg_m3",     "R",  "Current ore density"],
        ["1",    "0x0001", "thruster_temp_celsius",  "R",  "Primary thruster temp"],
        ["2",    "0x0002", "battery_percent",         "R",  "State-of-charge 0–100"],
        ["3",    "0x0003", "operational_status",      "R",  "0=IDLE 1=TRANSIT 2=DRILL 3=MINING 4=RTB"],
        ["4",    "0x0004", "sector_id",               "R",  "Current asteroid sector"],
        ["5",    "0x0005", "fault_flags",              "R",  "Bitmask — see Section 6"],
        ["1337", "0x0539", "DESTRUCT_AUTH",            "W",  "Write 0x4444 (unit 0x0A) to arm EDP"],
        ["2000–2017", "0x07D0–0x07E1", "DESTRUCT_CONFIRM", "R",  "Confirmation token — readable after EDP"],
    ]
    rt = wrapped_table(regs, col_widths=[2.1*cm, 2.3*cm, 3.5*cm, 1*cm, 6.6*cm])
    story.append(rt)

    doc.build(story)
    print(f"Generated: {OUTPUT}")


if __name__ == "__main__":
    build()
