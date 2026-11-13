"""
hmi_theme.py - deep-space theme for every RazorHack Perspective view.

One place for the look (starfield background, glass panels, neon accents) and
the four views built with it:
  ECLSSOverview  - gauges for O2 / CO2 / temperature, colored bars for the CDRA
                   beds, actuators and the nominal hold, alarm pills, MaintSync
  MaintConsole   - hidden maintenance terminal (carries the disarm code + flag)
  CrewManifest   - hidden archived page (carries the ghost-deck flag)
  TrainingHMI    - Training Bay console: beacon tuner (IG3), PLC link, IG2 label

Only component types confirmed for Ignition 8.3 are used: ia.container.coord,
ia.display.label, ia.display.markdown, ia.chart.gauge, ia.display.progress and
ia.input.numeric-entry-field. Everything else is CSS on labels.
"""

# ---------------------------------------------------------------- palette
INK = "#e6f3ff"        # primary text
DIM = "#6f8fb3"        # secondary text
HEAD = "#8fc6ff"       # card titles
GREEN = "#39e6a0"
AMBER = "#ffc857"
RED = "#ff4d6d"
CYAN = "#4cc9f0"
BLUE = "#4895ef"
VIOLET = "#9b5de5"
ORANGE = "#ff8c42"
TRACK = "rgba(120,160,220,0.16)"
MONO = "'Consolas','Menlo','Courier New',monospace"
SANS = "'Segoe UI','Roboto','Helvetica Neue',sans-serif"

STARFIELD = {
    "backgroundColor": "#050a16",
    "backgroundImage": ", ".join([
        "radial-gradient(1.5px 1.5px at 20px 30px, rgba(255,255,255,0.9), transparent)",
        "radial-gradient(1px 1px at 120px 80px, rgba(180,220,255,0.8), transparent)",
        "radial-gradient(1px 1px at 70px 150px, rgba(255,255,255,0.6), transparent)",
        "radial-gradient(1.5px 1.5px at 165px 170px, rgba(200,180,255,0.7), transparent)",
        "radial-gradient(1px 1px at 190px 20px, rgba(255,255,255,0.5), transparent)",
        "radial-gradient(ellipse at 12% 0%, rgba(40,110,255,0.24), transparent 55%)",
        "radial-gradient(ellipse at 95% 100%, rgba(150,60,255,0.22), transparent 55%)",
        "linear-gradient(180deg, #040814 0%, #070d1f 100%)",
    ]),
    "backgroundSize": "200px 200px, 200px 200px, 200px 200px, 200px 200px, 200px 200px, 100% 100%, 100% 100%, 100% 100%",
    "fontFamily": SANS,
}

GLASS = {
    "backgroundColor": "rgba(12,24,46,0.78)",
    "border": "1px solid rgba(90,170,255,0.28)",
    "borderRadius": "16px",
    "boxShadow": "0 0 28px rgba(30,120,255,0.12), inset 0 1px 0 rgba(255,255,255,0.05)",
}

GLOW = "0 0 14px rgba(80,200,255,0.55)"


# ---------------------------------------------------------------- builders
def _pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def _expr(expression):
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def label(name, x, y, w, h, text="", style=None, text_expr=None, style_exprs=None, align="left"):
    st = {"color": INK, "fontSize": "13px", "fontFamily": SANS}
    if align == "center":
        st.update({"textAlign": "center", "justifyContent": "center"})
    elif align == "right":
        st.update({"textAlign": "right", "justifyContent": "flex-end"})
    st.update(style or {})
    comp = {"type": "ia.display.label", "version": 0, "meta": {"name": name},
            "position": _pos(x, y, w, h), "props": {"text": text, "style": st}}
    cfg = {}
    if text_expr:
        cfg["props.text"] = _expr(text_expr)
    for prop, expression in (style_exprs or {}).items():
        cfg["props.style." + prop] = _expr(expression)
    if cfg:
        comp["propConfig"] = cfg
    return comp


def panel(name, x, y, w, h, title, accent=None):
    """Glass card + its title. Returns a list of components (card first)."""
    card = dict(GLASS)
    if accent:
        card["border"] = "1px solid " + accent
    return [
        label(name + "_card", x, y, w, h, "", card),
        label(name + "_title", x + 20, y + 14, w - 40, 22, title,
              {"color": HEAD, "fontSize": "12px", "fontWeight": 600, "letterSpacing": "0.24em"}),
    ]


def chip(name, x, y, w, h, text_expr, bg_expr, fg="#04121f"):
    return label(name, x, y, w, h, "", {
        "borderRadius": str(h // 2) + "px", "fontSize": "11px", "fontWeight": 700,
        "letterSpacing": "0.12em", "color": fg}, text_expr=text_expr,
        style_exprs={"backgroundColor": bg_expr}, align="center")


def gauge(name, x, y, w, h, value_expr, lo, hi, ranges):
    return {
        "type": "ia.chart.gauge", "version": 0, "meta": {"name": name},
        "position": _pos(x, y, w, h),
        "props": {
            "value": lo, "animate": True, "backgroundColor": "transparent",
            "outerAxis": {
                "data": "value", "show": True, "minValue": lo, "maxValue": hi,
                "width": 14, "color": TRACK, "percentRadius": 92,
                "ranges": [{"start": a, "end": b, "width": 14, "color": c} for a, b, c in ranges],
                "needle": {"origin": 0, "reach": 86, "color": INK},
                "tickMarks": {"color": "rgba(160,200,255,0.45)", "thickness": 1, "length": 6},
            },
            "innerAxis": {"show": False},
            "style": {"backgroundColor": "transparent"},
        },
        "propConfig": {"props.value": _expr(value_expr)},
    }


def bar(name, x, y, w, h, value_expr, hi, color=None, color_expr=None):
    comp = {
        "type": "ia.display.progress", "version": 0, "meta": {"name": name},
        "position": _pos(x, y, w, h),
        "props": {
            "min": 0, "max": hi, "value": 0, "mode": "determinate",
            "bar": {"color": color or CYAN, "style": {"borderRadius": str(h // 2) + "px",
                                                       "boxShadow": "0 0 12px rgba(76,201,240,0.35)"}},
            "track": {"color": TRACK, "style": {"borderRadius": str(h // 2) + "px"}},
            "valueDisplay": {"enabled": False},
            "style": {"borderRadius": str(h // 2) + "px", "overflow": "hidden"},
        },
        "propConfig": {"props.value": _expr(value_expr)},
    }
    if color_expr:
        comp["propConfig"]["props.bar.color"] = _expr(color_expr)
    return comp


def header(title, subtitle, w=1280):
    return [
        label("hdr_band", 0, 0, w, 72, "", {
            "backgroundImage": "linear-gradient(90deg, rgba(20,70,150,0.55), rgba(10,20,40,0.15))",
            "borderBottom": "1px solid rgba(90,170,255,0.35)"}),
        label("hdr_title", 32, 10, 760, 32, title, {
            "fontSize": "24px", "fontWeight": 700, "letterSpacing": "0.22em", "textShadow": GLOW}),
        label("hdr_sub", 32, 44, 760, 20, subtitle, {
            "color": "#6fa8dc", "fontSize": "11px", "letterSpacing": "0.32em"}),
    ]


def view(children, w=1280, h=800):
    return {
        "custom": {}, "params": {},
        "props": {"defaultSize": {"width": w, "height": h}},
        "root": {"type": "ia.container.coord", "version": 0, "meta": {"name": "root"},
                 "props": {"mode": "fixed", "style": dict(STARFIELD)}, "children": children},
    }


def markdown(name, x, y, w, h, source, color=INK, mono=True):
    return {"type": "ia.display.markdown", "version": 0, "meta": {"name": name},
            "position": _pos(x, y, w, h),
            "props": {"source": source, "style": {
                "color": color, "fontSize": "15px", "lineHeight": "1.6",
                "fontFamily": MONO if mono else SANS, "padding": "4px 8px"}}}


# ---------------------------------------------------------------- ECLSS overview
def T(n):
    return "{[default]ECLSS/Telemetry/%s}" % n


def S(n):
    return "{[default]ECLSS/Setpoints/%s}" % n


def eclss_overview(ship="ISV Ozark Horizon"):
    c = []
    c += header(ship.upper(), "ENVIRONMENTAL CONTROL & LIFE SUPPORT  ·  ECLSS")
    met = T("MET_s")
    c.append(label("met", 820, 14, 280, 44, "", {
        "fontFamily": MONO, "fontSize": "22px", "color": "#9fe8ff", "textShadow": GLOW,
        "letterSpacing": "0.08em"},
        text_expr="'MET  ' + numberFormat(floor(%s / 3600.0), '00') + ':' + "
                  "numberFormat(floor((%s %% 3600) / 60.0), '00') + ':' + numberFormat(%s %% 60, '00')"
                  % (met, met, met), align="right"))
    cs = T("CrewStatus")
    c.append(chip("crew_chip", 1116, 20, 140, 32,
                  "case(%s, 0, 'CREW NOMINAL', 1, 'CREW WARNING', 'CREW CRITICAL')" % cs,
                  "case(%s, 0, '%s', 1, '%s', '%s')" % (cs, GREEN, AMBER, RED)))

    # ---- three gauge cards
    def gauge_card(key, x, title, v, lo, hi, ranges, status_expr, color_expr, big_expr, sub_expr):
        y = 88
        out = panel(key, x, y, 392, 300, title)
        out.append(chip(key + "_status", x + 268, y + 12, 104, 24, status_expr, color_expr))
        out.append(gauge(key + "_gauge", x + 46, y + 44, 300, 170,
                         "min(max(%s, %s), %s)" % (v, lo, hi), lo, hi, ranges))
        out.append(label(key + "_value", x + 20, y + 212, 352, 44, "", {
            "fontFamily": MONO, "fontSize": "34px", "fontWeight": 700, "textShadow": GLOW},
            text_expr=big_expr, style_exprs={"color": color_expr}, align="center"))
        out.append(label(key + "_sub", x + 20, y + 258, 352, 22, "", {
            "color": DIM, "fontSize": "11px", "letterSpacing": "0.18em"},
            text_expr=sub_expr, align="center"))
        return out

    o2 = "(%s / 100.0)" % T("O2_x100")
    c += gauge_card(
        "o2", 32, "OXYGEN  ·  O2", o2, 0, 30,
        [(0, 19.5, RED), (19.5, 23.5, GREEN), (23.5, 30, AMBER)],
        "if(%s < 19.5, 'LOW', if(%s > 23.5, 'HIGH', 'NOMINAL'))" % (o2, o2),
        "if(%s < 19.5, '%s', if(%s > 23.5, '%s', '%s'))" % (o2, RED, o2, AMBER, GREEN),
        "numberFormat(%s, '0.00') + ' %%'" % o2,
        "'SETPOINT  ' + numberFormat(%s / 100.0, '0.00') + ' %%   ·   SAFE 19.5 - 23.5'" % S("O2_SP_x100"))

    co2 = T("CO2_ppm")
    c += gauge_card(
        "co2", 444, "CARBON DIOXIDE  ·  CO2", co2, 0, 10000,
        [(0, 5000, GREEN), (5000, 8000, AMBER), (8000, 10000, RED)],
        "if(%s > 8000, 'CRITICAL', if(%s > 5000, 'HIGH', 'NOMINAL'))" % (co2, co2),
        "if(%s > 8000, '%s', if(%s > 5000, '%s', '%s'))" % (co2, RED, co2, AMBER, GREEN),
        "numberFormat(%s, '#,##0') + ' ppm'" % co2,
        "'LIMIT  5,000 PPM'")

    t = "(%s / 100.0)" % T("Temp_x100")
    c += gauge_card(
        "temp", 856, "CABIN TEMPERATURE", t, 10, 40,
        [(10, 18, CYAN), (18, 27, GREEN), (27, 32, AMBER), (32, 40, RED)],
        "if(%s < 18, 'COLD', if(%s > 27, 'HOT', 'NOMINAL'))" % (t, t),
        "if(%s < 18, '%s', if(%s > 27, '%s', '%s'))" % (t, CYAN, t, RED, GREEN),
        "numberFormat(%s, '0.0') + ' °C'" % t,
        "'SETPOINT  ' + numberFormat(%s / 100.0, '0.0') + ' °C   ·   SAFE 18 - 27'" % S("Temp_SP_x100"))

    # ---- CDRA beds
    y = 404
    c += panel("cdra", 32, y, 604, 184, "CO2 REMOVAL  ·  CDRA BEDS")
    mode = S("CDRA_Mode")
    c.append(chip("cdra_mode", 32 + 420, y + 12, 164, 24,
                  "case(%s, 0, 'OFF', 1, 'AUTO SWING', 2, 'PINNED  BED A', 3, 'PINNED  BED B', 'UNKNOWN')" % mode,
                  "case(%s, 1, '%s', 0, '%s', '%s')" % (mode, GREEN, RED, AMBER)))
    act = T("ActiveBed")
    for i, (bed, tag) in enumerate((("A", "BedA_x10"), ("B", "BedB_x10"))):
        ry = y + 56 + i * 46
        sat = "(%s / 10.0)" % T(tag)
        c.append(label("bed%s_name" % bed, 52, ry, 70, 24, "BED " + bed, {
            "fontWeight": 700, "letterSpacing": "0.16em"}))
        c.append(chip("bed%s_state" % bed, 124, ry, 104, 24,
                      "if(%s = %d, 'ADSORBING', 'REGEN')" % (act, i + 1),
                      "if(%s = %d, '%s', '%s')" % (act, i + 1, CYAN, VIOLET)))
        c.append(bar("bed%s_bar" % bed, 240, ry + 2, 300, 20, sat, 100,
                     color_expr="if(%s >= 90, '%s', if(%s >= 60, '%s', '%s'))" % (sat, RED, sat, AMBER, GREEN)))
        c.append(label("bed%s_pct" % bed, 548, ry, 72, 24, "", {"fontFamily": MONO, "fontSize": "15px"},
                       text_expr="numberFormat(%s, '0') + ' %%'" % sat, align="right"))
    c.append(label("cdra_note", 52, y + 150, 564, 20, "", {"color": DIM, "fontSize": "11px", "letterSpacing": "0.12em"},
                   text_expr="'BEDS SWAP EVERY ' + %s + ' S  ·  A SATURATED BED STOPS SCRUBBING'" % S("CDRA_HalfCycle_s")))

    # ---- actuators
    c += panel("act", 656, y, 592, 184, "ACTUATORS")
    rows = (("OXYGEN GENERATOR", "OGA_x10", CYAN), ("COOLANT VALVE", "Valve_x10", BLUE), ("TRIM HEATER", "Heater_x10", ORANGE))
    for i, (name, tag, col) in enumerate(rows):
        ry = y + 54 + i * 40
        v = "(%s / 10.0)" % T(tag)
        key = tag.split("_")[0].lower()
        c.append(label(key + "_name", 676, ry, 180, 24, name, {"color": DIM, "fontSize": "11px", "letterSpacing": "0.16em"}))
        c.append(bar(key + "_bar", 860, ry + 2, 290, 20, v, 100, color=col))
        c.append(label(key + "_pct", 1156, ry, 72, 24, "", {"fontFamily": MONO, "fontSize": "15px"},
                       text_expr="numberFormat(%s, '0') + ' %%'" % v, align="right"))

    # ---- cabin
    y = 604
    c += panel("cabin", 32, y, 392, 172, "CABIN")
    hold = T("NominalHold_s")
    for i, (name, expr) in enumerate((
            ("PRESSURE", "numberFormat(%s / 10.0, '0.0') + ' kPa'" % T("Press_x10")),
            ("CREW ABOARD", "toStr(%s)" % T("CrewCount")))):
        ry = y + 50 + i * 30
        c.append(label("cab_n%d" % i, 52, ry, 170, 24, name, {"color": DIM, "fontSize": "11px", "letterSpacing": "0.16em"}))
        c.append(label("cab_v%d" % i, 232, ry, 172, 24, "", {"fontFamily": MONO, "fontSize": "17px"},
                       text_expr=expr, align="right"))
    c.append(label("hold_name", 52, y + 116, 170, 24, "NOMINAL HOLD", {"color": DIM, "fontSize": "11px", "letterSpacing": "0.16em"}))
    c.append(label("hold_val", 232, y + 116, 172, 24, "", {"fontFamily": MONO, "fontSize": "15px"},
                   text_expr="min(%s, 30) + ' / 30 s'" % hold, align="right"))
    c.append(bar("hold_bar", 52, y + 144, 352, 12, "min(%s, 30)" % hold, 30,
                 color_expr="if(%s >= 30, '%s', '%s')" % (hold, GREEN, CYAN)))

    # ---- alarms
    c += panel("alarms", 444, y, 392, 172, "ALARMS")
    aw = T("AlarmWord")
    pills = ((0, "O2 LOW", RED), (1, "O2 HIGH", AMBER), (2, "CO2 HIGH", RED),
             (3, "CABIN COLD", CYAN), (4, "CABIN HOT", RED), (5, "TAMPER", VIOLET))
    for i, (bit, text, col) in enumerate(pills):
        px = 464 + (i % 3) * 120
        py = y + 52 + (i // 3) * 44
        c.append(label("alarm_%d" % bit, px, py, 112, 32, text, {
            "borderRadius": "8px", "fontSize": "11px", "fontWeight": 700, "letterSpacing": "0.1em"},
            style_exprs={
                "backgroundColor": "if(getBit(%s, %d) = 1, '%s', 'rgba(255,255,255,0.04)')" % (aw, bit, col),
                "color": "if(getBit(%s, %d) = 1, '#04121f', '%s')" % (aw, bit, DIM),
                "boxShadow": "if(getBit(%s, %d) = 1, '0 0 16px %s', 'none')" % (aw, bit, col)},
            align="center"))
    c.append(label("alarm_word", 464, y + 142, 352, 20, "", {"color": DIM, "fontSize": "11px", "letterSpacing": "0.14em"},
                   text_expr="if(%s = 0, 'ALL SYSTEMS CLEAR', 'ACTIVE ALARMS  ·  WORD ' + %s)" % (aw, aw)))

    # ---- MaintSync
    sb = T("StatusBits")
    c += panel("maint", 856, y, 392, 172, "MAINTENANCE SYNC")
    c.append(label("maint_state", 876, y + 46, 352, 52, "", {
        "fontFamily": MONO, "fontSize": "34px", "fontWeight": 700, "letterSpacing": "0.2em"},
        text_expr="if(getBit(%s, 0) = 1, 'ARMED', 'DISARMED')" % sb,
        style_exprs={"color": "if(getBit(%s, 0) = 1, '%s', '%s')" % (sb, RED, GREEN),
                     "textShadow": "if(getBit(%s, 0) = 1, '0 0 18px %s', '0 0 18px %s')" % (sb, RED, GREEN)},
        align="center"))
    c.append(label("maint_note", 876, y + 102, 352, 22, "", {"color": DIM, "fontSize": "12px"},
                   text_expr="if(getBit(%s, 0) = 1, 'Commissioning baseline re-applies every 20 s', "
                             "'Setpoints are under crew control')" % sb, align="center"))
    c.append(label("maint_lock", 876, y + 130, 352, 22, "", {"color": AMBER, "fontSize": "11px",
                                                             "fontWeight": 700, "letterSpacing": "0.16em"},
                   text_expr="if(getBit(%s, 1) = 1, 'DISARM REGISTER LOCKED OUT', '')" % sb, align="center"))

    c.append(label("footer", 32, 780, 1216, 16, "", {"color": "#2e4a6b", "fontSize": "10px", "letterSpacing": "0.2em"},
                   text_expr="'RAZORHACK ICS  ·  OBJECTIVES ' + toStr(%s)" % T("FlagsEarned")))
    return view(c)


# ---------------------------------------------------------------- hidden ECLSS pages
def terminal_page(title, subtitle, badge, badge_color, body_md, w=1100, h=720):
    c = header(title, subtitle, w)
    c.append(label("badge", w - 220, 20, 188, 32, badge, {
        "backgroundColor": badge_color, "color": "#04121f", "borderRadius": "16px",
        "fontSize": "11px", "fontWeight": 700, "letterSpacing": "0.18em"}, align="center"))
    card = dict(GLASS)
    card["border"] = "1px solid " + badge_color
    c.append(label("term_card", 32, 96, w - 64, 260, "", card))
    c.append(markdown("term_text", 56, 116, w - 112, 220, body_md))
    return view(c, w, h)


# ---------------------------------------------------------------- Training console
def training_console(clue, ig2_flag, ig3_flag, w=1100, h=720):
    c = header("TRAINING BAY", "OPERATOR CONSOLE  ·  ISV OZARK HORIZON", w)
    hb = "{[default]Training/Heartbeat}"
    lock = "{[default]Training/IG3_Locked}"
    freq = "{[default]Training/Beacon_Freq}"

    # beacon tuner
    c += panel("beacon", 32, 96, 676, 420, "DEEP-SPACE BEACON TUNER")
    c.append(markdown("briefing", 52, 136, 636, 110,
                      "Tune the beacon to **%s**.  \nType the value and press **Enter** - the console writes it "
                      "to the PLC. The beacon holds lock for 30 s once the PLC confirms it." % clue,
                      color="#c9dcf0", mono=False))
    c.append(label("freq_lbl", 52, 262, 200, 20, "FREQUENCY  (MHz)", {"color": DIM, "fontSize": "11px", "letterSpacing": "0.18em"}))
    c.append({"type": "ia.input.numeric-entry-field", "version": 0, "meta": {"name": "FreqEntry"},
              "position": _pos(52, 286, 260, 52),
              "props": {"value": 0, "style": {
                  "backgroundColor": "rgba(4,10,24,0.9)", "color": "#9fe8ff", "fontFamily": MONO,
                  "fontSize": "26px", "border": "1px solid rgba(76,201,240,0.6)", "borderRadius": "10px",
                  "boxShadow": "0 0 18px rgba(76,201,240,0.25)"}},
              "propConfig": {"props.value": {"binding": {"type": "tag", "config": {
                  "mode": "direct", "tagPath": "[default]Training/Beacon_Freq", "bidirectional": True}}}}})
    c.append(chip("lock_chip", 336, 300, 168, 28,
                  "if(%s = 1, 'SIGNAL LOCKED', 'SEARCHING')" % lock,
                  "if(%s = 1, '%s', '%s')" % (lock, GREEN, AMBER)))
    c.append(label("sig_lbl", 52, 360, 200, 20, "SIGNAL LOCK", {"color": DIM, "fontSize": "11px", "letterSpacing": "0.18em"}))
    c.append(bar("sig_bar", 52, 384, 636, 18, "if(%s = 1, 100, 6)" % lock, 100,
                 color_expr="if(%s = 1, '%s', '%s')" % (lock, GREEN, AMBER)))
    c.append(label("BeaconStatus", 52, 420, 636, 72, "", {
        "fontFamily": MONO, "fontSize": "20px", "fontWeight": 700, "letterSpacing": "0.06em",
        "borderRadius": "10px", "padding": "0 16px"},
        text_expr="if(%s = 1, 'BEACON LOCKED   %s', 'NO LOCK  -  CHECK YOUR FREQUENCY')" % (lock, ig3_flag),
        style_exprs={"color": "if(%s = 1, '%s', '%s')" % (lock, GREEN, AMBER),
                     "backgroundColor": "if(%s = 1, 'rgba(57,230,160,0.10)', 'rgba(255,200,87,0.06)')" % lock,
                     "textShadow": "if(%s = 1, '0 0 16px %s', 'none')" % (lock, GREEN)},
        align="center"))

    # PLC link
    c += panel("link", 728, 96, 340, 200, "PLC LINK")
    c.append(label("hb_val", 748, 140, 300, 48, "", {
        "fontFamily": MONO, "fontSize": "30px", "fontWeight": 700, "color": "#9fe8ff", "textShadow": GLOW},
        text_expr="numberFormat(%s, '00000')" % hb, align="center"))
    c.append(label("hb_lbl", 748, 192, 300, 18, "HEARTBEAT  ·  +1 EVERY 100 ms", {
        "color": DIM, "fontSize": "10px", "letterSpacing": "0.18em"}, align="center"))
    c.append(bar("hb_bar", 748, 226, 300, 14, "%s %% 50" % hb, 49, color=CYAN))
    c.append(label("hb_note", 748, 252, 300, 20, "", {"color": DIM, "fontSize": "11px"},
                   text_expr="'LAST FREQUENCY WRITTEN  ' + %s" % freq, align="center"))

    # station notes
    c += panel("notes", 728, 316, 340, 200, "STATION NOTES")
    c.append(markdown("notes_md", 748, 352, 300, 150,
                      "- Training PLC: Modbus TCP, unit 1\n- Register map: `REGISTER_MAP.md`\n"
                      "- PLC logic: `TRAINING_LOGIC.st`\n- Successes hold ~20 s, then re-arm",
                      color="#c9dcf0", mono=False))

    # IG2: in the page, styled to be invisible
    c.append(label("SvcNote", w - 200, h - 18, 190, 12, ig2_flag, {
        "color": "transparent", "fontSize": "3px", "opacity": 0.02}))
    return view(c, w, h)
