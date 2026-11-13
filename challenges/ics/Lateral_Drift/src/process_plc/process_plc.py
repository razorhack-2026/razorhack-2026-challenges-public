"""
Last Mile — process-plc simulation (3/3 of the "Lateral Drift" sequence).

The controller for a Kalium-refinery enrichment centrifuge on the Keeper of Tomorrow, on Modbus/TCP,
with a live status page. The line spins raw Kalium feed gas through the rotor to enrich fuel-grade
Kalium for the main drive. The rotor has a critical speed (a resonance): at that speed it shakes,
wears its bearing and heats it, and the heat shifts the critical speed upward. The competitor unlocks
the controller with the factory-default code (from the commissioning sheet on the Lateral Drift
workstation), finds the resonance by sweeping the speed while watching vibration, then tracks it as
it drifts until the bearing seizes. The status page shows all of it live. After the seizure the
raw-Kalium feed vessel loses its draw-off and heats; the flag is shown when it reaches the melt
limit. Kalium enrichment (the product-quality readout) is display-only flavor, not part of the
attack.

Architecture (all in one process):
  - Ramp/process thread: the single writer of the process state. Ticks every DT seconds,
    reads the setpoint register, advances speed / vibration / bearing temp / wear, and mirrors
    the results into the Modbus registers.
  - Modbus/TCP server thread (pymodbus). A gated holding-register block implements the
    maintenance lock and clamps the setpoint.
  - Main thread: Flask. `/` serves the plain status page, `/api/state` serves the live state.
"""

import json
import logging
import math
import random
import sys
import threading
import time
from collections import deque

from flask import Flask, Response, jsonify
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer

from config import (
    HOST, MODBUS_PORT, STATUS_PORT, MODBUS_UNIT_ID, DT,
    HR_SETPOINT, HR_SAFE_LIMIT, HR_CURRENT_SPEED, HR_MAINT_UNLOCK, HR_LOCKOUT_SECONDS,
    HR_VIBRATION, HR_BEARING_TEMP, HR_BEARING_WEAR, HR_CORE_TEMP,
    COIL_TRIPPED, COIL_UNLOCKED,
    DEFAULT_UNLOCK_CODE, MAX_WRONG_CODES, LOCKOUT_SECONDS,
    NOMINAL_SPEED, SAFE_LIMIT, BEARING_AMBIENT, RAMP_RATE,
    BAND_CENTER0, BAND_DRIFT_PER_C, BAND_WIDTH,
    VIB_BASE, VIB_SPEED_SLOPE, VIB_PEAK, VIB_NOISE, VIB_ALERT,
    WEAR_THRESHOLD, WEAR_RATE, WEAR_RECOVERY, HEAT, COOL_TAU, TEMP_ALERT,
    CORE_TEMP_NOMINAL, CORE_HEAT_RATE, CORE_TEMP_ELEVATED, CORE_TEMP_CRITICAL, CORE_TEMP_MELT,
    PURITY_INIT, PURITY_TARGET, PURITY_GAIN, PURITY_DECAY, PURITY_MIN_SPEED,
    FLAG,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("process_plc")

FC_COIL = 1
FC_HOLDING = 3

T0 = time.time()
state_lock = threading.Lock()
S = {
    "speed": float(NOMINAL_SPEED),
    "setpoint": NOMINAL_SPEED,
    "vib": VIB_BASE + VIB_SPEED_SLOPE * NOMINAL_SPEED,
    "bearing": BEARING_AMBIENT,
    "wear": 0.0,
    "tripped": False,
    "core": CORE_TEMP_NOMINAL,
    "melted": False,
    "purity": float(PURITY_INIT),     # Kalium enrichment (%), display-only analyzer readout
}
events = deque(maxlen=40)          # newest last; shown on the status page
lock = {"unlocked": False, "wrong": 0, "until": 0.0}


def log_event(level, msg):
    events.append({"t": round(time.time() - T0, 1), "level": level, "msg": msg})
    log.info("[%s] %s", level, msg)


class GatedHoldingBlock(ModbusSequentialDataBlock):
    """Holding registers with the maintenance lock.

    Writes to the setpoint are dropped (no error, value unchanged) while locked, and clamped
    to safe_limit once unlocked. A write to HR_MAINT_UNLOCK is checked against the default
    code, never stored. Everything the simulator itself writes (speed, vibration, ...) goes
    through the same method, which is fine: it only gates the two addresses above.
    """

    def __init__(self, address, values, coils):
        super().__init__(address, values)
        self._coils = coils

    def setValues(self, address, values):
        if isinstance(values, int):
            values = [values]
        for offset, value in enumerate(values):
            addr = address + offset
            if addr == HR_MAINT_UNLOCK:
                self._try_unlock(value)
            elif addr == HR_SETPOINT:
                if not lock["unlocked"]:
                    log_event("warn", "setpoint write ignored: maintenance lock engaged")
                elif S["tripped"]:
                    log_event("warn", "setpoint write ignored: cascade scram latched")
                else:
                    super().setValues(addr, [max(0, min(SAFE_LIMIT, value))])
            else:
                super().setValues(addr, [value])

    def _try_unlock(self, code):
        now = time.monotonic()
        if lock["unlocked"]:
            return
        if now < lock["until"]:
            log_event("warn", "unlock attempt ignored: register locked out")
            return
        if code == DEFAULT_UNLOCK_CODE:
            lock["unlocked"], lock["wrong"] = True, 0
            self._coils.setValues(COIL_UNLOCKED, [True])
            log_event("ok", "MAINTENANCE MODE: setpoint writes enabled")
            return
        lock["wrong"] += 1
        log_event("warn", "wrong unlock code (%d/%d)" % (lock["wrong"], MAX_WRONG_CODES))
        if lock["wrong"] >= MAX_WRONG_CODES:
            lock["wrong"], lock["until"] = 0, now + LOCKOUT_SECONDS
            log_event("bad", "unlock register locked out for %d s" % LOCKOUT_SECONDS)


def build_context() -> ModbusServerContext:
    """Construct the shared Modbus datastore with power-on defaults."""
    coils = ModbusSequentialDataBlock(0, [False] * 8)   # C0 scram_tripped, C1 maint_unlocked
    hr = GatedHoldingBlock(
        0,
        [
            NOMINAL_SPEED,                # HR0 rotor_speed_setpoint
            SAFE_LIMIT,                   # HR1 safe_limit
            NOMINAL_SPEED,                # HR2 current_speed
            0,                            # HR3 maint_unlock (write-only)
            0,                            # HR4 lockout_seconds
            int(S["vib"] * 10),           # HR5 vibration x10
            int(BEARING_AMBIENT),         # HR6 bearing_temp
            0,                            # HR7 bearing_wear
            int(CORE_TEMP_NOMINAL),       # HR8 feed_vessel_temp
            0, 0, 0,                      # padding
        ],
        coils,
    )
    di = ModbusSequentialDataBlock(0, [False] * 8)
    ir = ModbusSequentialDataBlock(0, [0] * 8)
    # zero_mode=True: PDU address N maps to block index N. Without it pymodbus adds 1 to
    # every address, shifting the whole register map — the bug class already hit (and fixed)
    # in Containment Breach's and Blind Spot's sims.
    slave = ModbusSlaveContext(di=di, co=coils, hr=hr, ir=ir, zero_mode=True)
    return ModbusServerContext(slaves=slave, single=True)


def band_center(bearing: float) -> float:
    """The resonance speed (%): moves up as the bearing heats."""
    return BAND_CENTER0 + BAND_DRIFT_PER_C * max(0.0, bearing - BEARING_AMBIENT)


def vibration(speed: float, bearing: float) -> float:
    d = (speed - band_center(bearing)) / BAND_WIDTH
    return (VIB_BASE + VIB_SPEED_SLOPE * speed + VIB_PEAK * math.exp(-d * d)
            + random.uniform(-VIB_NOISE, VIB_NOISE))


def process_model(context: ModbusServerContext) -> None:
    """Daemon thread: the only writer of the process state."""
    marks = {"vib": False, "temp": False, "w50": False, "w80": False, "elev": False, "crit": False}
    log_event("info", "controller online, maintenance lock engaged")

    while True:
        time.sleep(DT)
        slave = context[MODBUS_UNIT_ID]
        now = time.monotonic()

        with state_lock:
            if S["tripped"]:
                setpoint = 0                                  # coast down after the seizure
            else:
                setpoint = max(0, min(SAFE_LIMIT, slave.getValues(FC_HOLDING, HR_SETPOINT, count=1)[0]))
            S["setpoint"] = setpoint

            speed = S["speed"]
            if speed < setpoint:
                speed = min(setpoint, speed + RAMP_RATE)
            elif speed > setpoint:
                speed = max(setpoint, speed - RAMP_RATE)
            S["speed"] = speed

            vib = vibration(speed, S["bearing"])
            if S["tripped"]:
                vib *= speed / max(1.0, float(SAFE_LIMIT))    # noise dies as it spins down
            S["vib"] = vib

            if not S["tripped"]:
                if vib > WEAR_THRESHOLD:
                    S["wear"] += WEAR_RATE * (vib - WEAR_THRESHOLD) / (VIB_BASE + VIB_PEAK - WEAR_THRESHOLD) * DT
                else:
                    S["wear"] -= WEAR_RECOVERY * DT
                S["wear"] = max(0.0, min(100.0, S["wear"]))
                heat = HEAT * max(0.0, vib - 3.0)
                S["bearing"] += (heat - (S["bearing"] - BEARING_AMBIENT) / COOL_TAU) * DT
            else:
                S["bearing"] = min(140.0, S["bearing"] + 1.5 * DT)

            if S["wear"] >= 100.0 and not S["tripped"]:
                S["tripped"] = True
                slave.setValues(FC_COIL, COIL_TRIPPED, [True])
                log_event("bad", "ROTOR BEARING SEIZURE: cascade scram latched")

            if S["tripped"] and not S["melted"]:
                S["core"] += CORE_HEAT_RATE * DT          # no draw-off: the feed vessel heats
                if S["core"] >= CORE_TEMP_MELT:
                    S["melted"] = True
                    log_event("bad", "FEED VESSEL MELTDOWN: temperature past the melt limit")
            if S["core"] > CORE_TEMP_ELEVATED and not marks["elev"]:
                marks["elev"] = True
                log_event("warn", "FEED VESSEL TEMPERATURE ELEVATED: draw-off lost")
            if S["core"] > CORE_TEMP_CRITICAL and not marks["crit"]:
                marks["crit"] = True
                log_event("bad", "FEED VESSEL TEMPERATURE CRITICAL")

            if vib > VIB_ALERT and not marks["vib"]:
                marks["vib"] = True
                log_event("warn", "ROTOR VIBRATION HIGH on centrifuge C-2")
            elif vib < VIB_ALERT - 2.0:
                marks["vib"] = False
            if S["bearing"] > TEMP_ALERT and not marks["temp"]:
                marks["temp"] = True
                log_event("warn", "BEARING TEMP HIGH")
            if S["wear"] >= 50 and not marks["w50"]:
                marks["w50"] = True
                log_event("warn", "bearing wear above 50 %")
            if S["wear"] >= 80 and not marks["w80"]:
                marks["w80"] = True
                log_event("bad", "bearing wear above 80 %: failure imminent")

            # Kalium enrichment (display-only analyzer readout; not a Modbus register and
            # not part of the attack). Climbs toward fuel grade while the line runs normally,
            # stalls while the rotor is driven into the resonance band, and falls back toward
            # raw feed once the bearing seizes and the draw-off is lost.
            if not S["tripped"] and speed >= PURITY_MIN_SPEED and vib < WEAR_THRESHOLD:
                S["purity"] += PURITY_GAIN * (PURITY_TARGET - S["purity"]) * DT
            elif S["tripped"]:
                S["purity"] = max(PURITY_INIT, S["purity"] - PURITY_DECAY * DT)
            S["purity"] = max(0.0, min(100.0, S["purity"]))

            snap = dict(S)

        slave.setValues(FC_HOLDING, HR_CURRENT_SPEED, [int(round(snap["speed"]))])
        slave.setValues(FC_HOLDING, HR_VIBRATION, [int(round(snap["vib"] * 10))])
        slave.setValues(FC_HOLDING, HR_BEARING_TEMP, [int(round(snap["bearing"]))])
        slave.setValues(FC_HOLDING, HR_BEARING_WEAR, [int(round(snap["wear"]))])
        slave.setValues(FC_HOLDING, HR_CORE_TEMP, [int(round(min(snap["core"], 65000)))])
        slave.setValues(FC_HOLDING, HR_LOCKOUT_SECONDS,
                        [max(0, int(round(lock["until"] - now + 0.49)))])


app = Flask(__name__)


def phase_and_alarm(snap):
    """Name of the plant state, for the status page and /api/state."""
    if snap["melted"]:
        return "MELTDOWN", "FEED VESSEL MELTDOWN"
    if snap["tripped"]:
        if snap["core"] > CORE_TEMP_CRITICAL:
            return "CRITICAL", "FEED VESSEL TEMPERATURE CRITICAL"
        if snap["core"] > CORE_TEMP_ELEVATED:
            return "ELEVATED", "FEED VESSEL TEMPERATURE ELEVATED"
        return "ROTOR FAILURE", "ROTOR BEARING SEIZURE: CASCADE SCRAM LATCHED"
    if snap["vib"] > VIB_ALERT:
        return "WARNING", "VIBRATION HIGH"
    if snap["bearing"] > TEMP_ALERT:
        return "WARNING", "BEARING TEMP HIGH"
    return "NOMINAL", "NORMAL"


def current_state():
    with state_lock:
        snap = dict(S)
    phase, alarm = phase_and_alarm(snap)
    body = {
        "t": round(time.time() - T0, 1),
        "phase": phase,
        "alarm": alarm,
        "speed": round(snap["speed"], 1),
        "setpoint": snap["setpoint"],
        "safe_limit": SAFE_LIMIT,
        "vib": round(snap["vib"], 2),
        "bearing": round(snap["bearing"], 1),
        "wear": round(snap["wear"], 1),
        "core": round(snap["core"], 1),
        "purity": round(snap["purity"], 1),
        "tripped": snap["tripped"],
        "unlocked": lock["unlocked"],
        "lockout": max(0, int(round(lock["until"] - time.monotonic() + 0.49))),
        "events": list(events)[-14:],
    }
    if snap["melted"]:
        body["flag"] = FLAG          # only once the feed vessel passes the melt limit
    return body


# The operator status page. Presentation only: it reads everything live from /api/state
# (polled by the JS below) and shows nothing the API doesn't. The simulation, the Modbus
# map and the flag-at-meltdown rule are untouched by anything in this template. CFG holds
# the static alarm limits (so the gauges can draw their zones); INIT is the snapshot at
# page load (so a plain `curl /` still shows current state and, at meltdown, the flag).
STATUS_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RC-200 HMI - Kalium Refinery Line 2</title>
<style>
/* Dated Windows-classic intranet chrome, matched to the Lateral Drift engineering
   portal (navy title bar, beige panels, blue headers, Tahoma, beveled inset fields).
   A web-served PLC panel from the same plant-engineering shop would look like this. */
*{box-sizing:border-box}
html,body{margin:0}
body{background:#d4d0c8;color:#1a1a1a;font-family:Tahoma,"Segoe UI",Arial,sans-serif;font-size:12px}
#hmi{max-width:1100px;margin:0 auto;padding:8px}
.titlebar{display:flex;justify-content:space-between;align-items:center;background:#0a246a;color:#fff;
 border:1px solid #000;padding:5px 10px;flex-wrap:wrap;gap:6px}
.titlebar .co{font-weight:700;letter-spacing:.3px}
.titlebar .sep{color:#9fb0e0;margin:0 6px}
.tb-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.tag{background:#dfe6f5;border:1px solid #000;padding:1px 6px;color:#0a246a;font-family:"Courier New",monospace}
.pill{font-family:"Courier New",monospace;font-size:12px}
.pill.live{color:#7ef0a6} .pill.stale{color:#ff8c8c}
.clock{font-family:"Courier New",monospace;color:#fff}
.oper{color:#c3cdee;font-size:12px}
.alarmbar{display:flex;align-items:center;gap:14px;margin-top:5px;padding:6px 12px;background:#ece9d8;
 border:1px solid #808080;border-top-color:#fff;border-left-color:#fff;flex-wrap:wrap}
.alarmbar .phase{font-weight:700;letter-spacing:1px;font-family:"Courier New",monospace;padding:1px 10px;
 border:1px solid #000;background:#2f9e5a;color:#fff}
.alarmbar.warn .phase{background:#cf8a1e} .alarmbar.bad .phase{background:#c0241a}
.alarmbar .alarmtext{font-weight:700;color:#1a1a1a}
.alarmbar .runstate{margin-left:auto;font-family:"Courier New",monospace;color:#444}
.alarmbar.warn{background:#f6e6bf} .alarmbar.bad{background:#f3d2cf;border-color:#c0241a}
@keyframes blink{50%{opacity:.45}}
.alarmbar.bad.blink .phase{animation:blink 1s step-end infinite}
.grid{display:grid;grid-template-columns:1.4fr 1fr;gap:8px;margin-top:8px}
@media(max-width:900px){.grid{grid-template-columns:1fr}.span2{grid-column:auto}}
.panel{background:#ece9d8;border:1px solid #808080;min-width:0}
.panel-hd{background:#245edb;color:#fff;border-bottom:1px solid #1a3a8f;padding:3px 8px;font-size:11px;
 letter-spacing:.5px;font-weight:700;text-transform:uppercase}
.panel-bd{padding:10px}
.span2{grid-column:1 / span 2}
.mimic-wrap{display:flex;flex-direction:column;gap:8px}
svg#mimic{width:100%;height:auto;background:#f7f6f1;border:1px solid #808080}
.lamps{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.lamp{display:flex;align-items:center;gap:6px;font-size:12px;color:#444;font-family:"Courier New",monospace}
.lamp b{color:#000}
.led{width:11px;height:11px;border-radius:50%;background:#b8b4a8;border:1px solid #000;display:inline-block}
.led.ok{background:#2f9e5a} .led.warn{background:#e0a21e} .led.bad{background:#d8281c} .led.off{background:#b8b4a8}
.lamp-note{margin-left:auto;color:#b25f00;font-family:"Courier New",monospace;font-size:12px;font-weight:700}
.fp{margin-bottom:12px}
.fp:last-child{margin-bottom:0}
.fp-row{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.fp-name{color:#333;font-size:11px;font-family:"Courier New",monospace;letter-spacing:.5px}
.fp-val{font-family:"Courier New",monospace;font-size:20px;color:#000;background:#fff;
 border:1px solid #7f9db9;border-top-color:#404040;border-left-color:#404040;padding:1px 8px;min-width:96px;text-align:right}
.fp-val .u{font-size:11px;color:#666;margin-left:4px}
.fp-val.warn{color:#b25f00} .fp-val.bad{color:#c0241a}
.bar{position:relative;height:13px;background:#fff;border:1px solid #808080;border-top-color:#404040;border-left-color:#404040;margin-top:6px}
.bar-fill{position:absolute;left:0;top:0;bottom:0;width:0%;background:#245edb}
.bar-fill.ok{background:#2f9e5a} .bar-fill.warn{background:#cf8a1e} .bar-fill.bad{background:#c0241a}
.mk{position:absolute;top:-2px;bottom:-2px;width:2px}
.mk.safe{background:#c0241a} .mk.setp{background:#0a246a;box-shadow:0 0 0 1px #fff} .mk.alert{background:#cf8a1e} .mk.bad{background:#c0241a}
.sub{display:flex;justify-content:space-between;color:#555;font-size:11px;font-family:"Courier New",monospace;margin-top:3px}
.gauge-wrap{display:flex;gap:12px;align-items:center}
svg#vibgauge{width:190px;height:116px;flex:none}
#vibgauge .z{fill:none;stroke-width:12}
#vibgauge .hub{fill:#ece9d8;stroke:#000}
#vibgauge #vibneedle{stroke:#000;stroke-width:3;stroke-linecap:round}
#vibgauge text{fill:#555;font-size:9px;font-family:"Courier New",monospace}
@keyframes spin{to{transform:rotate(360deg)}}
#rotor{animation:spin 2s linear infinite;transform-box:fill-box;transform-origin:center}
svg text.mimlbl{fill:#333;font-family:"Courier New",monospace;font-size:10px}
svg text.mim-val{fill:#000;font-family:"Courier New",monospace;font-size:13px;font-weight:700}
#mimic tspan.u{font-size:10px;fill:#666;font-weight:400}
table.evt{width:100%;border-collapse:collapse;font-family:"Courier New",monospace;font-size:12px}
table.evt td{border-bottom:1px solid #cfcbbf;padding:2px 6px}
table.evt tr:nth-child(even){background:#f4f2ea}
table.evt .et{color:#555;width:54px;text-align:right}
table.evt .em{color:#1a1a1a}
.sevtag{font-size:10px;padding:0 5px;border:1px solid currentColor;font-weight:700}
.sevtag.ok{color:#1a7d3c} .sevtag.warn{color:#b25f00} .sevtag.bad{color:#c0241a} .sevtag.info{color:#666}
.flagcard{max-width:1100px;margin:8px auto 0;border:2px solid #c0241a;background:#fff}
.flagcard-hd{background:#c0241a;color:#fff;font-weight:700;padding:4px 10px;letter-spacing:1px}
.flagcode{font-family:"Courier New",monospace;font-size:18px;color:#a0110b;padding:12px 10px;word-break:break-all}
</style>
</head>
<body>
<div id="hmi">
  <div class="titlebar">
    <div class="tb-left"><span class="co">RazerPowerCo</span><span class="sep">|</span>KEEPER OF TOMORROW<span class="sep">|</span>Kalium Refinery / Line 2</div>
    <div class="tb-right">
      <span class="tag">RC-200 / C-2</span>
      <span id="conn" class="pill live">LINK OK</span>
      <span id="clock" class="clock">--:--:--</span>
      <span class="oper">OPER refinery2</span>
    </div>
  </div>
  <div id="alarmbar" class="alarmbar ok">
    <span id="phase" class="phase">----</span>
    <span id="alarm" class="alarmtext">----</span>
    <span id="runstate" class="runstate"></span>
  </div>
  <div class="grid">
    <div class="panel">
      <div class="panel-hd">Process Overview &mdash; Centrifuge C-2 / Feed Vessel V-205</div>
      <div class="panel-bd mimic-wrap">
        <svg id="mimic" viewBox="0 0 420 220">
          <rect x="2" y="2" width="416" height="216" fill="none" stroke="#c9c5b8"/>
          <text class="mimlbl" x="95" y="46" text-anchor="middle">C-2 CENTRIFUGE</text>
          <rect x="40" y="52" width="110" height="104" rx="6" fill="#e8e6dd" stroke="#808080"/>
          <g id="rotor">
            <circle cx="95" cy="104" r="34" fill="#ffffff" stroke="#245edb"/>
            <line x1="95" y1="70" x2="95" y2="138" stroke="#245edb" stroke-width="2"/>
            <line x1="61" y1="104" x2="129" y2="104" stroke="#245edb" stroke-width="2"/>
            <line x1="71" y1="80" x2="119" y2="128" stroke="#7aa0d8" stroke-width="1.5"/>
            <line x1="119" y1="80" x2="71" y2="128" stroke="#7aa0d8" stroke-width="1.5"/>
          </g>
          <text id="m_speed" class="mim-val" x="95" y="178" text-anchor="middle"><tspan id="m_speed_n">0</tspan><tspan class="u" dx="2">%</tspan></text>
          <line x1="150" y1="104" x2="268" y2="104" stroke="#9a968b" stroke-width="6"/>
          <polygon points="260,98 272,104 260,110" fill="#9a968b"/>
          <text id="drawoff" x="209" y="94" text-anchor="middle" style="font-family:'Courier New',monospace;font-size:11px;fill:#1a7d3c">DRAW-OFF OK</text>
          <text class="mimlbl" x="315" y="40" text-anchor="middle">V-205 FEED VESSEL</text>
          <clipPath id="tankclip"><rect x="272" y="50" width="86" height="126" rx="9"/></clipPath>
          <rect id="tankfill" x="272" y="138" width="86" height="38" fill="#5a8fd0" clip-path="url(#tankclip)"/>
          <rect x="270" y="48" width="90" height="130" rx="8" fill="none" stroke="#808080"/>
          <text id="m_core" class="mim-val" x="315" y="118" text-anchor="middle"><tspan id="m_core_n">0</tspan><tspan class="u" dx="2">&deg;C</tspan></text>
        </svg>
        <div class="lamps">
          <span class="lamp"><i id="scram_led" class="led ok"></i>CASCADE SCRAM <b id="scram_st">ARMED</b></span>
          <span class="lamp"><i id="maint_led" class="led off"></i>MAINT MODE <b id="maint_st">LOCKED</b></span>
          <span id="lockout" class="lamp-note"></span>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">Rotor</div>
      <div class="panel-bd">
        <div class="fp">
          <div class="fp-row"><span class="fp-name">SI-201 ROTOR SPEED</span><span id="v_speed" class="fp-val">0.0<span class="u">%</span></span></div>
          <div class="bar"><div id="bar_speed" class="bar-fill ok"></div><div id="mk_safe" class="mk safe"></div><div id="mk_setpoint" class="mk setp"></div></div>
          <div class="sub"><span id="s_setpoint">SP --</span><span id="s_safe">SAFE --</span></div>
        </div>
        <div class="fp">
          <div class="fp-row"><span class="fp-name">VT-201 ROTOR VIBRATION</span><span id="v_vib" class="fp-val">0.00<span class="u">mm/s</span></span></div>
          <div class="gauge-wrap">
            <svg id="vibgauge" viewBox="0 0 200 116">
              <path id="z_ok" class="z"/><path id="z_warn" class="z"/><path id="z_bad" class="z"/>
              <line id="vibneedle" x1="100" y1="100" x2="100" y2="28"/>
              <circle class="hub" cx="100" cy="100" r="6"/>
              <text x="16" y="112">0</text><text x="100" y="112" text-anchor="middle">10</text><text x="176" y="112" text-anchor="end">20</text>
            </svg>
            <div class="sub" style="flex-direction:column;gap:3px;align-items:flex-start">
              <span>WEAR THR 6.0</span><span style="color:#b25f00">ALARM 7.0</span><span style="color:#c0241a">PEAK ~15</span>
            </div>
          </div>
        </div>
        <div class="fp">
          <div class="fp-row"><span class="fp-name">AT-201 KALIUM ENRICHMENT</span><span id="v_purity" class="fp-val">0.0<span class="u">%</span></span></div>
          <div class="bar"><div id="bar_purity" class="bar-fill ok"></div><div id="mk_puritytgt" class="mk setp"></div></div>
          <div class="sub"><span>RAW FEED 72</span><span>FUEL-GRADE 99.5</span></div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">Bearing</div>
      <div class="panel-bd">
        <div class="fp">
          <div class="fp-row"><span class="fp-name">TT-202 BEARING TEMP</span><span id="v_btemp" class="fp-val">0.0<span class="u">&deg;C</span></span></div>
          <div class="bar"><div id="bar_btemp" class="bar-fill ok"></div><div id="mk_talert" class="mk alert"></div></div>
          <div class="sub"><span>AMB 40</span><span>HI 85</span></div>
        </div>
        <div class="fp">
          <div class="fp-row"><span class="fp-name">WI-201 BEARING WEAR</span><span id="v_wear" class="fp-val">0.0<span class="u">%</span></span></div>
          <div class="bar"><div id="bar_wear" class="bar-fill ok"></div><div class="mk alert" style="left:50%"></div><div class="mk bad" style="left:80%"></div></div>
          <div class="sub"><span>WARN 50</span><span>SEIZE 100</span></div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">Feed Vessel V-205</div>
      <div class="panel-bd">
        <div class="fp">
          <div class="fp-row"><span class="fp-name">TT-205 VESSEL TEMP</span><span id="v_core" class="fp-val">0<span class="u">&deg;C</span></span></div>
          <div class="bar"><div id="bar_core" class="bar-fill ok"></div><div id="mk_celev" class="mk alert"></div><div id="mk_ccrit" class="mk bad"></div></div>
          <div class="sub"><span>NOM 320</span><span>MELT 1200</span></div>
        </div>
        <div class="fp" style="color:#555;font-family:'Courier New',monospace;font-size:12px;line-height:1.5">
          Draw-off of enriched product from centrifuge C-2 holds the raw-Kalium feed vessel near 320 &deg;C. A cascade scram stops the draw-off; the vessel then heats at about 40 &deg;C/s.
        </div>
      </div>
    </div>
    <div class="panel span2">
      <div class="panel-hd">Alarm &amp; Event Summary</div>
      <div class="panel-bd" style="padding:4px 0;max-height:172px;overflow:auto">
        <table class="evt"><tbody id="events"></tbody></table>
      </div>
    </div>
  </div>
</div>
<div id="flaghost">__FLAGBANNER__</div>
<noscript><p style="font-family:monospace;padding:12px">Live HMI needs a browser. Raw controller state: <a href="/api/state">/api/state</a></p></noscript>
<script>
var CFG=__CFG__, INIT=__INIT__;
function el(id){return document.getElementById(id);}
function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
function pct(v,mn,mx){return (clamp((v-mn)/(mx-mn),0,1)*100).toFixed(2)+'%';}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function pt(f,r){var a=Math.PI*(1-f);return [100+r*Math.cos(a),100-r*Math.sin(a)];}
function arcPath(f0,f1,r){var A=pt(f0,r),B=pt(f1,r);
  // every zone lies within the 180-deg dial, so the large-arc flag is always 0.
  return 'M '+A[0].toFixed(1)+' '+A[1].toFixed(1)+' A '+r+' '+r+' 0 0 1 '+B[0].toFixed(1)+' '+B[1].toFixed(1);}
function zone(id,f0,f1,c){var e=el(id);e.setAttribute('d',arcPath(f0,f1,76));e.setAttribute('stroke',c);}
function valClass(id,sev){var e=el(id);e.className='fp-val'+(sev==='ok'?'':' '+sev);}
function flagCard(f){return '<div class="flagcard"><div class="flagcard-hd">EVIDENCE &mdash; FEED VESSEL MELTDOWN</div>'
  +'<div class="flagcode">'+esc(f)+'</div></div>';}
function init(){
  el('mk_safe').style.left=pct(CFG.safeLimit,0,CFG.speedMax);
  el('mk_talert').style.left=pct(CFG.tempAlert,CFG.tempMin,CFG.tempMax);
  el('mk_celev').style.left=pct(CFG.coreElev,CFG.coreMin,CFG.coreMax);
  el('mk_ccrit').style.left=pct(CFG.coreCrit,CFG.coreMin,CFG.coreMax);
  el('mk_puritytgt').style.left=pct(CFG.purityTarget,0,100);
  zone('z_ok',0,CFG.vibWear/CFG.vibMax,'#2f9e5a');
  zone('z_warn',CFG.vibWear/CFG.vibMax,CFG.vibAlert/CFG.vibMax,'#cf8a1e');
  zone('z_bad',CFG.vibAlert/CFG.vibMax,1,'#d8281c');
}
function setTank(core,sev){
  var f=clamp((core-CFG.coreMin)/(CFG.coreMax-CFG.coreMin),0,1);var full=126,h=f*full;
  var r=el('tankfill');r.setAttribute('y',(176-h).toFixed(1));r.setAttribute('height',h.toFixed(1));
  r.setAttribute('fill',sev==='bad'?'#c0241a':(sev==='warn'?'#cf8a1e':'#5a8fd0'));
}
function sev3(v,warn,bad){return v>=bad?'bad':(v>=warn?'warn':'ok');}
function renderEvents(evs){
  var rows=evs.slice().reverse().map(function(e){
    var s=e.level==='ok'?'ok':(e.level==='warn'?'warn':(e.level==='bad'?'bad':'info'));
    return '<tr><td class="et">'+Number(e.t).toFixed(1)+'</td><td><span class="sevtag '+s+'">'+esc(e.level.toUpperCase())
      +'</span></td><td class="em">'+esc(e.msg)+'</td></tr>';}).join('');
  el('events').innerHTML=rows||'<tr><td class="em">no events</td></tr>';
}
function render(s){
  var sev=s.phase==='NOMINAL'?'ok':(s.phase==='WARNING'?'warn':'bad');
  el('alarmbar').className='alarmbar '+sev+((s.phase==='MELTDOWN'||s.phase==='CRITICAL')?' blink':'');
  el('phase').textContent=s.phase; el('alarm').textContent=s.alarm;
  el('runstate').textContent=s.tripped?'ROTOR STOPPED':(s.unlocked?'MAINT ENABLED':'RUN');
  el('v_speed').innerHTML=Number(s.speed).toFixed(1)+'<span class="u">%</span>';
  el('bar_speed').style.width=pct(s.speed,0,CFG.speedMax);
  el('mk_setpoint').style.left=pct(s.setpoint,0,CFG.speedMax);
  el('s_setpoint').textContent='SP '+s.setpoint; el('s_safe').textContent='SAFE '+s.safe_limit;
  var vs=sev3(s.vib,CFG.vibWear,CFG.vibAlert);
  el('v_vib').innerHTML=Number(s.vib).toFixed(2)+'<span class="u">mm/s</span>'; valClass('v_vib',vs);
  var f=clamp(s.vib/CFG.vibMax,0,1);
  el('vibneedle').setAttribute('transform','rotate('+(-90+f*180).toFixed(1)+' 100 100)');
  var ts=s.bearing>=CFG.tempAlert?'warn':'ok';
  el('v_btemp').innerHTML=Number(s.bearing).toFixed(1)+'<span class="u">&deg;C</span>'; valClass('v_btemp',ts);
  el('bar_btemp').className='bar-fill '+(s.bearing>=CFG.tempAlert?'bad':'ok'); el('bar_btemp').style.width=pct(s.bearing,CFG.tempMin,CFG.tempMax);
  var ws=sev3(s.wear,CFG.wearWarn,CFG.wearBad);
  el('v_wear').innerHTML=Number(s.wear).toFixed(1)+'<span class="u">%</span>'; valClass('v_wear',ws);
  el('bar_wear').className='bar-fill '+ws; el('bar_wear').style.width=pct(s.wear,0,100);
  var cs=s.core>=CFG.coreCrit?'bad':(s.core>=CFG.coreElev?'warn':'ok');
  el('v_core').innerHTML=Number(s.core).toFixed(0)+'<span class="u">&deg;C</span>'; valClass('v_core',cs);
  el('bar_core').className='bar-fill '+cs; el('bar_core').style.width=pct(s.core,CFG.coreMin,CFG.coreMax);
  el('v_purity').innerHTML=Number(s.purity).toFixed(1)+'<span class="u">%</span>';
  el('bar_purity').style.width=pct(s.purity,0,100);
  el('bar_purity').className='bar-fill '+(s.purity>=95?'ok':'warn');
  el('m_speed_n').textContent=Number(s.speed).toFixed(0);
  el('m_core_n').textContent=Number(s.core).toFixed(0); setTank(s.core,cs);
  var ro=el('rotor');
  if(s.speed>1 && !s.tripped){ro.style.animationDuration=Math.max(0.3,120/s.speed).toFixed(2)+'s';ro.style.animationPlayState='running';}
  else{ro.style.animationPlayState='paused';}
  el('drawoff').textContent=s.tripped?'DRAW-OFF LOST':'DRAW-OFF OK';
  el('drawoff').style.fill=s.tripped?'#c0241a':'#1a7d3c';
  el('scram_led').className='led '+(s.tripped?'bad':'ok'); el('scram_st').textContent=s.tripped?'LATCHED':'ARMED';
  el('maint_led').className='led '+(s.unlocked?'warn':'off'); el('maint_st').textContent=s.unlocked?'ENABLED':'LOCKED';
  el('lockout').textContent=s.lockout>0?('UNLOCK LOCKOUT '+s.lockout+'s'):'';
  renderEvents(s.events||[]);
  el('flaghost').innerHTML=s.flag?flagCard(s.flag):'';
}
function setConn(ok){var c=el('conn');c.textContent=ok?'LINK OK':'NO LINK';c.className='pill '+(ok?'live':'stale');}
function poll(){
  fetch('/api/state',{cache:'no-store'}).then(function(r){return r.json();})
    .then(function(s){render(s);setConn(true);}).catch(function(){setConn(false);})
    .then(function(){setTimeout(poll,500);});
}
function tick(){var d=new Date();el('clock').textContent=d.toLocaleTimeString([],{hour12:false});}
init(); render(INIT); setConn(true); tick(); setInterval(tick,1000); poll();
</script>
</body>
</html>"""


@app.route("/")
def status_page():
    st = current_state()
    cfg = {
        "speedMax": 100, "safeLimit": SAFE_LIMIT, "nominal": NOMINAL_SPEED,
        "vibMax": 20.0, "vibWear": WEAR_THRESHOLD, "vibAlert": VIB_ALERT,
        "tempMin": float(BEARING_AMBIENT), "tempMax": 150.0, "tempAlert": TEMP_ALERT,
        "wearWarn": 50.0, "wearBad": 80.0,
        "coreMin": 300.0, "coreMax": CORE_TEMP_MELT + 100.0,
        "coreElev": CORE_TEMP_ELEVATED, "coreCrit": CORE_TEMP_CRITICAL, "coreMelt": CORE_TEMP_MELT,
        "purityTarget": PURITY_TARGET, "purityRaw": PURITY_INIT,
    }
    flag_banner = ""
    if "flag" in st:
        # Server-rendered so a plain `curl /` still sees the flag at meltdown, exactly as
        # before. Same gate as /api/state: present only once the feed vessel has melted.
        flag_banner = ('<div class="flagcard"><div class="flagcard-hd">EVIDENCE &mdash; FEED VESSEL MELTDOWN</div>'
                       '<div class="flagcode">%s</div></div>') % st["flag"]
    html = (STATUS_SHELL
            .replace("__CFG__", json.dumps(cfg))
            .replace("__INIT__", json.dumps(st))
            .replace("__FLAGBANNER__", flag_banner))
    return Response(html, mimetype="text/html")


@app.route("/api/state")
def api_state():
    resp = jsonify(current_state())
    resp.headers["Cache-Control"] = "no-store"
    return resp


def main() -> None:
    log.info("Initialising Last Mile process-plc simulation ...")
    context = build_context()
    threading.Thread(target=process_model, args=(context,), daemon=True, name="process-model").start()
    threading.Thread(
        target=StartTcpServer, kwargs={"context": context, "address": (HOST, MODBUS_PORT)},
        daemon=True, name="modbus-server",
    ).start()
    log.info("Modbus/TCP on %s:%d unit=%d;  status page + /api/state on %s:%d",
             HOST, MODBUS_PORT, MODBUS_UNIT_ID, HOST, STATUS_PORT)
    app.run(host=HOST, port=STATUS_PORT, threaded=True)


if __name__ == "__main__":
    main()
