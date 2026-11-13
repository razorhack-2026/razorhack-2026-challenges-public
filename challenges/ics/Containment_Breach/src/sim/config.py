# sim/config.py — all tunables live here; no magic numbers in the simulation loop.

import os

# ── Network ──────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"  # the competitor-facing multi-unit port (PORT_MULTI)
# The four per-device ports are for the Ignition gateway, which shares this
# container's network namespace (one Fargate task per team; network_mode
# service:sim in docker-compose.yml), so they listen on loopback only.
# DEVICE_HOST=0.0.0.0 opens them up again, e.g. for a gateway in another container.
DEVICE_HOST = os.environ.get("DEVICE_HOST", "127.0.0.1")
MODBUS_UNIT_ID = 1  # every endpoint below is single-slave; unit ID is always 1

# Each vessel + the shared plant is its own Modbus/TCP listener on its own
# port — simpler and lower-risk than multi-unit-ID addressing on one port,
# and each Ignition device config is a straight copy of the others.
PORT_VESSEL_A = 502  # "Culture Bay 1" — directly attackable, unchanged mechanics
PORT_VESSEL_B = 503  # "Culture Bay 2" — directly attackable, unchanged mechanics
PORT_VESSEL_C = 504  # "Founder Culture" — hardened, flag vessel
PORT_PLANT    = 505  # Cryo Plant — read-only shared-capacity telemetry

# Competitor-facing endpoint: ONE port serving all four devices as Modbus unit IDs
# (instance topics hand each team a single {port}). Same datastores as the four
# listeners above, which stay for the Ignition gateway.
PORT_MULTI = 5030
UNIT_VESSEL_A, UNIT_VESSEL_B, UNIT_VESSEL_C, UNIT_PLANT = 1, 2, 3, 4

# ── Timing ───────────────────────────────────────────────────────────────────
DT = 0.5  # Growth-model tick interval (seconds)

# ── Per-vessel initial conditions / dynamics ──────────────────────────────────
# All three vessels share identical tuning — only the plant's shared capacity
# and Vessel C's local lockout make them behave differently.
NOMINAL_INCUBATION_TEMP = 40    # percent (0–100)
BASELINE_DENSITY        = 250   # Dormant-floor density (register value; display = 25.0)
BREACH_THRESHOLD        = 1200  # Vessel rupture threshold (register value; display = 120.0)
K_GROWTH                = 0.6   # Density units gained per % incubation-temp per tick

# ── Shared cryo plant ──────────────────────────────────────────────────────────
#
# Each vessel has its own writable coolant_valve_pct register — how far open
# its cooling valve is, nominally 30% (throttled). The device enforces a hard
# cap at COOLANT_VALVE_MAX (100): any write above that is accepted at the
# protocol level but clamped back to 100 within one tick, the same
# "accepted then reverted" behavior Vessel C's HOA lockout already has.
#
# Each vessel with suppression ON *demands* coolant_valve_pct * K_DEMAND units
# of cooling per tick. The plant has a fixed TOTAL_CAPACITY shared across all
# vessels currently demanding cooling, and rations proportionally to each
# vessel's own request:
#
#   total_demand = sum(valve_pct_i * K_DEMAND for vessel i with suppression ON)
#   ratio        = min(1.0, TOTAL_CAPACITY / total_demand)
#   suppression_level_i = round(valve_pct_i * ratio)   (per ON vessel; 0 if OFF)
#
# Because ratio is always <= 1.0 and valve_pct_i is capped at 100, actual
# received cooling can NEVER exceed the vessel's own valve request — a vessel
# can only ever be throttled relative to what it asked for, never over-cooled
# past it. (This is why the old over-100%-cooling "cryo lockup" mechanic is
# gone: it's no longer physically possible once writes are capped.)
#
# TOTAL_CAPACITY is sized for *exactly* nominal 3-vessel simultaneous demand,
# with zero headroom — a deliberate, realistic detail (plants are routinely
# provisioned for nominal load with no margin, a real root cause in
# cascading-failure postmortems):
#   3 vessels x 30 units nominal demand = 90 = TOTAL_CAPACITY
#
# Stability check at nominal (all three valve=30%, suppression=30%):
#   total_demand = 3 x 30 = 90 = TOTAL_CAPACITY  →  ratio = 1.0
#   suppress_out = 30 x K_SUPPRESS(1.0) = 30/tick ; growth_in = 40 x 0.6 = 24/tick
#   net = −6/tick  →  clamps at BASELINE  ✓  (all three vessels stable)
#
# Overload path — push A and/or B's valves up to the 100% cap (C stays locked
# at nominal 30, same HOA mechanism as its temp/coil):
#   total_demand = 100 + 100 + 30 = 230  →  ratio = 90/230 ≈ 0.3913
#   Vessel A/B actual cooling = round(100 x 0.3913) ≈ 39% — MORE than their
#   nominal 30%, so they drift slightly cooler and sit dormant at baseline —
#   a harmless side effect, never a breach.
#   Vessel C's actual cooling = round(30 x 0.3913) ≈ 12% — starved, even
#   though its own valve and temp never moved: suppress_out=12/tick ;
#   growth_in starts at 40x0.6=24/tick and accelerates with climbing temp
#   (thermal runaway) → breaches from heat in roughly 20-25s; re-verify live,
#   this sim's own feedback loop isn't reliable to hand-calculate past tick 1.
K_SUPPRESS      = 1.0   # Density units removed per % suppression per tick (per vessel)
K_DEMAND        = 1.0   # Cooling units demanded per % coolant-valve-open per tick
TOTAL_CAPACITY  = 90    # Shared cryo-plant capacity, units/tick (= 3 x nominal demand)

COOLANT_VALVE_DEFAULT = 30   # percent open, nominal (throttled)
COOLANT_VALVE_MAX     = 100  # hard device cap — writes above this clamp back to 100

# ── Thermal dynamics — incubation_temp is now a live simulated state, not an
# attacker-writable input. Every vessel generates a constant baseline of
# metabolic heat; the cooling it actually receives (suppression_level, from
# the shared-plant math above) pulls that back down. Reproduction rate is
# driven by this live temperature, not a fixed setpoint — so starving a
# vessel of cooling doesn't just stop its cooling, it lets temperature climb,
# which directly accelerates its own growth: a genuine thermal-runaway
# feedback loop, not just a static imbalance.
#
#   heat_in     = BASE_HEAT_GEN                         (constant, per vessel)
#   cooling_out = suppression_level * K_TEMP_COOL
#   temp       += (heat_in − cooling_out) * TEMP_RATE    (clamped 0–100)
#   growth_in   = temp * K_GROWTH                         (same formula, live temp)
#
# Tuned so nominal (suppression=30%, the throttled default) is a true
# equilibrium — heat_in exactly cancels cooling_out, so temp sits flat at
# NOMINAL_INCUBATION_TEMP forever unless suppression actually changes:
#   BASE_HEAT_GEN = 12, K_TEMP_COOL = 0.4  →  cooling_out(30%) = 12 = heat_in  ✓
#
# TEMP_RATE throttles how fast temperature actually moves per tick (thermal
# inertia), so the rise/fall is visibly watchable (several seconds) rather
# than snapping to the clamp in one or two ticks:
#   A/B drawn up to valve=100%, actual cooling=39%: cooling_out=39x0.4=15.6,
#   net=-3.6, scaled by TEMP_RATE(0.06) = -0.22/tick — temp drifts down
#   slowly; density stays clamped at baseline (never breaches, no COLD path
#   exists any more — a hard 100% cap means actual cooling can never exceed
#   a vessel's own valve request, so over-cooling past 100% is impossible).
#   C starved to suppression=12%: cooling_out=12x0.4=4.8, net=+7.2, scaled
#   = +0.43/tick — temp visibly climbs, and because growth_in = temp*K_GROWTH
#   uses that same live value, C's own reproduction rate accelerates as it
#   heats up (the runaway effect), eventually breaching from heat. Verify
#   actual breach timing live — re-tune TEMP_RATE if it's off from a
#   15-30 min overall solve budget; don't trust hand-calculation past tick 1
#   for this feedback loop.
BASE_HEAT_GEN = 12    # % heat generated per tick, constant per vessel
K_TEMP_COOL   = 0.4   # temp points removed per % suppression per tick
TEMP_RATE     = 0.06  # thermal inertia — fraction of net heat actually applied per tick

# ── Over-cooling side effects on the directly-attacked vessels (A/B) ──────────
# Flavor only — NONE of this is read by the breach logic, so it never gates or
# accelerates Vessel C's flag breach. Forcing a vessel's own coolant valve
# above nominal floods it with coolant. The shared-plant rationing means its
# *received* cooling barely rises (valve 100 -> ~39% actual), but the local
# over-pressure still stresses that culture: the colony shrinks slightly toward
# a dormant floor and its membrane integrity (viability_pct, the "MEMBRANE
# INTEG." bar) is progressively compromised. Both effects are driven purely by
# how far the valve is pushed past COOLANT_VALVE_DEFAULT (the "overdrive"), so
# Vessel C — whose valve is locked at nominal — has overdrive 0, keeps full
# membrane integrity, and grows to breach exactly as before.
#
#   overdrive        = max(0, coolant_valve_pct - COOLANT_VALVE_DEFAULT)   (0..70)
#   viability_pct   -= overdrive * MEMBRANE_WEAR_RATE   (floored at MEMBRANE_MIN)
#   density floor    = OVERCOOL_DENSITY_FLOOR while overdrive > 0 (vs BASELINE)
#
# At valve=100 (overdrive 70): membrane loses 70*0.06=4.2/tick -> from 100 to
# compromised-red (<33) in ~8s, to the MEMBRANE_MIN floor in ~11s; density
# settles ~22.0 (a slight shrink from the 25.0 baseline). Valve returned to
# nominal lets membrane slowly recover (MEMBRANE_RECOVER/tick). Re-verify live.
MEMBRANE_WEAR_RATE     = 0.06   # viability % lost per % valve-overdrive per tick
MEMBRANE_RECOVER       = 1.5    # viability % regained per tick when valve <= nominal
MEMBRANE_MIN           = 12     # floor — compromised, not destroyed (A/B never "die")
OVERCOOL_DENSITY_FLOOR = 220    # register (display 22.0) — slight dormant shrink below BASELINE_DENSITY (250)

# ── Vessel C — local HOA lockout ───────────────────────────────────────────────
# Modeled as a physical Hand-Off-Auto selector left in HAND (local control): a
# ubiquitous real industrial-equipment concept. Every tick, before the growth
# model runs, Vessel C's coolant_valve_pct and suppression_system coil are
# force-rewritten back to these fixed values — a remote write is accepted at
# the protocol level but visibly reverts within one tick (~0.5s). Its
# incubation_temp needs no separate lock: temperature is simulation-computed
# for every vessel now, so it was never attacker-writable to begin with. The
# SHARED plant capacity Vessel C depends on is NOT locked, which is the point.
VESSEL_C_LOCKED_VALVE = COOLANT_VALVE_DEFAULT
VESSEL_C_LOCKED_SUPPRESSION = True

# ── Flag ──────────────────────────────────────────────────────────────────────
# The simulator does not know, store, or serve the flag — it only drives the
# breach coil. The single live copy the contestant sees is the static label in
# the Ignition popup view (ContainmentBreachPopup), fired by Vessel C's breach
# coil; the canonical value lives in challenge.yml (and solution/).
#
# Deliberately NOT defined here: this file is COPYd into the sim Docker image,
# so keeping the flag out of config.py prevents it leaking in an image layer.
# See src/ignition/BINDINGS.md for the popup label to keep in sync.
