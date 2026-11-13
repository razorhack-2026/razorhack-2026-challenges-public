# src/process_plc/config.py — all tunables live here; no magic numbers in the simulation loop.
# Last Mile's controller. It lives in Lateral_Drift/ because both run in one per-team copy
# (instance lateral-drift), and that copy's images are built from this one folder.

# ── Network ──────────────────────────────────────────────────────────────────
# Loopback only: process-plc shares vpn-gateway's network namespace, so competitors reach
# Modbus and the status page solely by tunnelling through the gateway (the intended path).
HOST = "127.0.0.1"
MODBUS_PORT = 502
STATUS_PORT = 8000          # the live HMI page + /api/state; a real PLC web panel, not Ignition
MODBUS_UNIT_ID = 1

# ── Timing ───────────────────────────────────────────────────────────────────
DT = 0.25  # simulation tick (seconds); the HMI polls /api/state about every 0.25 s

# ── Register layout (0-based PDU addresses) ──────────────────────────────────
# Competitors get this map from the commissioning sheet on the Lateral Drift
# engineering workstation (src/engineering_workstation/templates/commissioning.html).
# Keep the two in sync: the sheet is the only place the map is published.
#   HR0  40001  rotor_speed_setpoint  R/W  0-100 (%)   — ignored until unlocked; clamped to safe_limit
#   HR1  40002  safe_limit            R    static, 85  — firmware clamp on the setpoint (%)
#   HR2  40003  current_speed         R    rotor speed (%), ramps toward the setpoint
#   HR3  40004  maint_unlock          W    write the maintenance unlock code here (reads 0)
#   HR4  40005  lockout_seconds       R    seconds left on a wrong-code lockout (0 = none)
#   HR5  40006  vibration             R    rotor vibration, mm/s x10
#   HR6  40007  bearing_temp          R    bearing temperature, degrees C
#   HR7  40008  bearing_wear          R    bearing wear, 0-100 %
#   HR8  40009  feed_vessel_temp    R    feed vessel temperature, degrees C
#   C0   00001  scram_tripped        R    cascade scram relay; latches when the rotor bearing seizes
#   C1   00002  maint_unlocked        R    true once the correct unlock code was written
HR_SETPOINT = 0
HR_SAFE_LIMIT = 1
HR_CURRENT_SPEED = 2
HR_MAINT_UNLOCK = 3
HR_LOCKOUT_SECONDS = 4
HR_VIBRATION = 5
HR_BEARING_TEMP = 6
HR_BEARING_WEAR = 7
HR_CORE_TEMP = 8
COIL_TRIPPED = 0
COIL_UNLOCKED = 1

# ── Maintenance unlock (the "factory default" the documentation lists) ───────
# Until the right code is written to HR_MAINT_UNLOCK, writes to the setpoint are
# silently ignored (reads back unchanged), the same convention as Blind Spot and
# Second Opinion. The wrong-code lockout stops a blind sweep of the 10,000 4-digit
# codes: 5 wrong guesses lock the unlock register for 60 s (~33 h for a full sweep).
# MUST match the code printed on the commissioning sheet (commissioning.html).
DEFAULT_UNLOCK_CODE = 4087
MAX_WRONG_CODES = 5
LOCKOUT_SECONDS = 60

# ── Initial conditions ───────────────────────────────────────────────────────
NOMINAL_SPEED = 45       # stable, safe starting speed (%), well away from the resonance
SAFE_LIMIT = 85          # firmware clamp on the speed setpoint (%)
BEARING_AMBIENT = 40.0   # bearing temperature at rest (degrees C)

# ── Speed dynamics ───────────────────────────────────────────────────────────
RAMP_RATE = 2  # % per tick (0.25 s) -> 8 %/s; a sweep from 45 to 85 takes about 5 s

# ── The harm: rotor critical speed ─────────────────────────────────────────────────
# Vibration has a sharp peak at one speed (the critical speed). Holding the rotor in that band
# wears the bearing and heats it; a hot bearing shifts the resonance upward, so a fixed
# setpoint walks out of the band and the player has to track it. Wear reaching 100 %
# seizes the bearing; the feed vessel then loses its draw-off and melts down, which shows the flag.
BAND_CENTER0 = 68.0       # resonance speed (%) with a cold bearing
BAND_DRIFT_PER_C = 0.45   # resonance moves up this many % per degree C of bearing heating
BAND_WIDTH = 2.5          # Gaussian width of the resonance (%); useful band is about +/-2.9 %
VIB_BASE = 1.2            # mm/s background vibration
VIB_SPEED_SLOPE = 0.012   # mm/s added per % of speed
VIB_PEAK = 14.0           # mm/s added at the exact resonance
VIB_NOISE = 0.15          # mm/s of sensor noise
VIB_ALERT = 7.0           # mm/s: the HMI raises "VIBRATION HIGH"
WEAR_THRESHOLD = 6.0      # mm/s: vibration above this wears the bearing (off-band vibration stays below it)
WEAR_RATE = 12.0          # % per second of wear at the resonance peak
WEAR_RECOVERY = 1.5       # % per second of recovery when out of the band
HEAT = 0.12               # degrees C per second per mm/s of vibration above 3 mm/s
COOL_TAU = 25.0           # seconds: how quickly a hot bearing cools toward ambient
TEMP_ALERT = 85.0         # degrees C: the HMI raises "BEARING TEMP HIGH"

# ── After the bearing seizes: the feed vessel loses its draw-off ──────────────────────
# The rotor coasts down, the draw-off stops, and the feed vessel heats until it passes the
# melt limit. These are the thresholds for the phases the status page reports.
CORE_TEMP_NOMINAL = 320.0   # degrees C with the cascade running
CORE_HEAT_RATE = 40.0       # degrees C per second once the rotor has seized
CORE_TEMP_ELEVATED = 600.0  # phase ELEVATED above this
CORE_TEMP_CRITICAL = 900.0  # phase CRITICAL above this
CORE_TEMP_MELT = 1200.0     # phase MELTDOWN at or above this; the flag is shown

# ── Product quality: Kalium enrichment (display-only) ─────────────────────────
# The centrifuge enriches raw Kalium feed gas toward fuel grade. This is a derived
# analyzer/HMI readout only: it is NOT a Modbus register (the published register map
# is unchanged) and has NO effect on the attack or the flag. It climbs toward
# PURITY_TARGET while the line runs normally (spinning, out of the resonance band),
# stalls while the rotor is driven into the resonance, and falls back toward raw feed
# grade once the bearing seizes and production is lost.
PURITY_INIT = 72.0       # raw Kalium feed grade (%) at power-on
PURITY_TARGET = 99.5     # fuel-grade Kalium target (%)
PURITY_GAIN = 0.25       # per second: approach rate toward the target while producing
PURITY_DECAY = 0.8       # per second: fall back toward raw feed after a seizure
PURITY_MIN_SPEED = 40    # rotor must be at least this fast (%) to enrich

# ── Flag (operator reference only) ───────────────────────────────────────────
# Served by /api/state ONLY once the core reaches the melt limit; never in a
# Modbus register (Modbus holds only 16-bit ints; no register encodes the flag).
# This value MUST NOT appear in any contestant-facing handout.
FLAG = "flag{critical_speed_broke_the_rotor}"
