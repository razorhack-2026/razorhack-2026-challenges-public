"""
Containment Breach — ICS/OT CTF challenge simulation.

Three bio-containment vessels culturing Ignis vorax, a thermophilic
microorganism that feeds on heat energy, share one finite cryo-suppression
plant. Each vessel's temperature is a live simulated state (not a direct
input): constant metabolic heat in, cooling out — so starving a vessel of
cooling lets its own temperature climb, which directly accelerates its own
reproduction rate (a genuine thermal-runaway feedback loop). Vessels A and B
are directly attackable via their coolant valve, which nominally sits
throttled at COOLANT_VALVE_DEFAULT (30%) and is hard-capped by the device at
COOLANT_VALVE_MAX (100%) — a write above that is accepted at the protocol
level but clamped back to 100 within one tick. Vessel C is hardened — a
local Hand-Off-Auto lockout reverts any remote write to its valve/coil
within one tick — so it can only be breached by starving the SHARED plant
capacity via A and/or B.

Architecture:
  - Four independent Modbus/TCP listeners, one per vessel + one for the
    plant's read-only telemetry, each its own daemon thread running a
    blocking pymodbus TCP server against its own ModbusServerContext.
  - One shared growth-model daemon thread ticks all four contexts together
    every DT seconds: computes the shared allocation ratio, applies it to
    each vessel's real suppression_level, re-locks Vessel C's own setpoint,
    and runs each vessel's growth/breach model.
"""

import math
import sys
import threading
import time
import logging

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer

from config import (
    HOST, DEVICE_HOST, MODBUS_UNIT_ID,
    PORT_VESSEL_A, PORT_VESSEL_B, PORT_VESSEL_C, PORT_PLANT,
    PORT_MULTI, UNIT_VESSEL_A, UNIT_VESSEL_B, UNIT_VESSEL_C, UNIT_PLANT,
    DT,
    NOMINAL_INCUBATION_TEMP,
    BASELINE_DENSITY,
    BREACH_THRESHOLD,
    K_GROWTH,
    K_SUPPRESS,
    K_DEMAND,
    TOTAL_CAPACITY,
    COOLANT_VALVE_DEFAULT,
    COOLANT_VALVE_MAX,
    BASE_HEAT_GEN,
    K_TEMP_COOL,
    TEMP_RATE,
    MEMBRANE_WEAR_RATE,
    MEMBRANE_RECOVER,
    MEMBRANE_MIN,
    OVERCOOL_DENSITY_FLOOR,
    VESSEL_C_LOCKED_VALVE,
    VESSEL_C_LOCKED_SUPPRESSION,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("containment_sim")

# ── Function-code aliases (pymodbus convention) ───────────────────────────────
FC_COIL    = 1   # read coils / write coil(s)
FC_HOLDING = 3   # read holding registers / write register(s)

# ── Per-vessel register layout: 0-based PDU addresses (identical on A/B/C) ───
#   PDU 0  ↔  40001  incubation_temp
#   PDU 1  ↔  40002  colony_density
#   PDU 2  ↔  40003  breach_threshold
#   PDU 3  ↔  40004  suppression_level   (actual cooling received, can exceed 100%)
#   PDU 4  ↔  40005  coolant_valve_pct   (R/W — how far open the cooling valve is;
#                                          nominal 30%, device hard-caps at 100%)
#   PDU 5  ↔  40006  viability_pct       (R — specimen vitals, 100=healthy, 0=lost)
HR_INCUBATION_TEMP   = 0
HR_COLONY_DENSITY    = 1
HR_BREACH_THRESHOLD  = 2
HR_SUPPRESSION_LEVEL = 3
HR_COOLANT_VALVE     = 4
HR_VIABILITY         = 5

#   PDU 0  ↔  00001  suppression_system
#   PDU 1  ↔  00002  breach  (undocumented to contestants)
COIL_SUPPRESSION = 0
COIL_BREACH      = 1

# ── Plant register layout (read-only) ─────────────────────────────────────────
#   PDU 0  ↔  40001  total_capacity  (static)
#   PDU 1  ↔  40002  total_demand    (live)
#   PDU 2  ↔  40003  allocation_pct  (live, x1 — not x10 like density)
HR_PLANT_CAPACITY   = 0
HR_PLANT_DEMAND     = 1
HR_PLANT_ALLOCATION = 2

VESSEL_NAMES = ("A", "B", "C")

class GuardedBlock(ModbusSequentialDataBlock):
    """Datablock where only `writable` addresses accept a Modbus client write.

    A client write to any other address is accepted at the protocol level
    (no exception, same as Vessel C's HOA lockout) but silently dropped, so it
    never reaches the datastore, not even for one tick. The simulation writes
    through `_sim_set`, which bypasses this guard.
    """

    def __init__(self, address, values, writable=()):
        super().__init__(address, values)
        self._writable = frozenset(writable)

    def setValues(self, address, values):  # client writes arrive here
        if not isinstance(values, (list, tuple)):
            values = [values]
        for offset, value in enumerate(values):
            if address + offset in self._writable:
                super().setValues(address + offset, [value])

    def set_internal(self, address, values):
        super().setValues(address, values)


def _sim_set(slave, fc, address, values):
    """Simulation-side write: bypasses the client-write guard."""
    store = slave.store["c" if fc == FC_COIL else "h"]
    store.set_internal(address, values)



def build_vessel_context() -> ModbusServerContext:
    """Construct one vessel's Modbus datastore with power-on defaults."""
    hr = GuardedBlock(
        0,
        [
            NOMINAL_INCUBATION_TEMP,  # HR 0 — incubation_temp
            BASELINE_DENSITY,         # HR 1 — colony_density  (sim-driven)
            BREACH_THRESHOLD,         # HR 2 — breach_threshold (static)
            COOLANT_VALVE_DEFAULT,    # HR 3 — suppression_level (nominal, ratio=1.0 at power-on)
            COOLANT_VALVE_DEFAULT,    # HR 4 — coolant_valve_pct (R/W, nominal throttled 30%)
            100,                      # HR 5 — viability_pct (100% = healthy)
            0, 0,                     # padding
        ],
        writable=(HR_COOLANT_VALVE,),
    )
    # Only the suppression coil takes a client write; the breach coil is set by the model alone.
    coils = GuardedBlock(
        0,
        [
            True,   # Coil 0 — suppression_system  ON
            False,  # Coil 1 — breach              NOT triggered
            False, False, False, False,  # padding
        ],
        writable=(COIL_SUPPRESSION,),
    )
    di = ModbusSequentialDataBlock(0, [False] * 8)
    ir = ModbusSequentialDataBlock(0, [0] * 8)

    # zero_mode=True: PDU address N maps to block index N. Without it pymodbus adds 1 to every address, which
    # shifts the whole register map (HR0 would read density, the breach coil would read as suppression).
    slave = ModbusSlaveContext(di=di, co=coils, hr=hr, ir=ir, zero_mode=True)
    return ModbusServerContext(slaves=slave, single=True)


def build_plant_context() -> ModbusServerContext:
    """Construct the read-only plant telemetry datastore."""
    hr = GuardedBlock(
        0,
        [
            TOTAL_CAPACITY,  # HR 0 — total_capacity (static)
            TOTAL_CAPACITY,  # HR 1 — total_demand   (starts == capacity at nominal)
            100,             # HR 2 — allocation_pct (starts at 100%)
            0, 0, 0, 0, 0,   # padding
        ],
    )
    di = ModbusSequentialDataBlock(0, [False] * 8)
    co = GuardedBlock(0, [False] * 8)
    ir = ModbusSequentialDataBlock(0, [0] * 8)
    slave = ModbusSlaveContext(di=di, co=co, hr=hr, ir=ir, zero_mode=True)
    return ModbusServerContext(slaves=slave, single=True)


def growth_model(contexts: dict) -> None:
    """
    Daemon thread: shared cryo-plant + three-vessel growth model.

    Each tick (DT seconds), for each vessel i with suppression ON:
        demand_i = coolant_valve_pct_i * K_DEMAND
    ratio = min(1.0, TOTAL_CAPACITY / sum(demand_i))
    suppression_level_i = round(coolant_valve_pct_i * ratio)   (0 if coil OFF)

    This is proportional rationing. Every vessel's coolant_valve_pct is
    hard-capped at COOLANT_VALVE_MAX (100) before demand is computed, so
    ratio <= 1.0 always and a vessel's actual received cooling can never
    exceed its own request — only ever throttled relative to it, never
    over-cooled past it. Pushing a vessel's own valve up increases its own
    demand on the shared pool, which shrinks everyone else's share instead.

    incubation_temp is now a LIVE SIMULATED STATE, not an attacker-writable
    input — every vessel generates a constant baseline of metabolic heat each
    tick; the cooling it actually receives (suppression_level) pulls that
    back down. Reproduction rate is driven by this live temperature:
        heat_in     = BASE_HEAT_GEN
        cooling_out = suppression_level * K_TEMP_COOL
        temp       += (heat_in − cooling_out) * TEMP_RATE   (clamped 0–100)
        growth_in   = temp * K_GROWTH
        suppress_out = suppression_level * K_SUPPRESS
        density      = max(BASELINE_DENSITY, density + growth_in − suppress_out)
    This is a genuine thermal-runaway feedback loop: starving a vessel of
    cooling lets its temperature climb, which directly accelerates its own
    growth — not just a static imbalance. The register is overwritten with
    the freshly computed temperature every tick, so a direct write to it
    (the old "overfeed" technique) has no lasting effect on any vessel.

    One breach condition, wired to the breach coil: HEAT — density >
    BREACH_THRESHOLD. Pushing A/B's valves up starves the shared plant,
    which only ever increases their own received cooling (never decreases
    it below nominal), so A/B themselves can't breach this way — only
    Vessel C, whose own valve never moves, gets starved and heats up.

    Vessel C's coolant_valve_pct and suppression_system coil are
    force-rewritten to their locked values every tick BEFORE demand is
    computed, modeling a local Hand-Off-Auto lockout — remote writes are
    accepted by the protocol but revert within one tick. The shared plant
    capacity is not locked, which is the whole point: only C's breach
    reveals the flag (wired in the Ignition HMI).
    """
    density = {name: float(BASELINE_DENSITY) for name in VESSEL_NAMES}
    temp = {name: float(NOMINAL_INCUBATION_TEMP) for name in VESSEL_NAMES}
    membrane = {name: 100.0 for name in VESSEL_NAMES}  # viability_pct accumulator
    breached = {name: False for name in VESSEL_NAMES}
    tick = 0
    # Per-vessel phase offset so the three tubes don't visibly wobble in lockstep.
    jitter_phase = {"A": 0.0, "B": 2.1, "C": 4.2}

    log.info(
        "Growth model started — K_growth=%.1f  K_suppress=%.1f  K_demand=%.1f  "
        "capacity=%d  DT=%.1fs",
        K_GROWTH, K_SUPPRESS, K_DEMAND, TOTAL_CAPACITY, DT,
    )

    while True:
        time.sleep(DT)
        tick += 1

        vessel_slaves = {name: contexts[name][MODBUS_UNIT_ID] for name in VESSEL_NAMES}
        plant_slave = contexts["plant"][MODBUS_UNIT_ID]

        # ── Vessel C local lockout: re-assert before anything else reads it ──
        _sim_set(vessel_slaves["C"], FC_HOLDING, HR_COOLANT_VALVE, [VESSEL_C_LOCKED_VALVE])
        _sim_set(vessel_slaves["C"], FC_COIL, COIL_SUPPRESSION, [VESSEL_C_LOCKED_SUPPRESSION])

        # ── Read writable registers (incubation_temp is sim-computed, not read here) ──
        coolant_valve = {}
        suppression_on = {}
        for name in VESSEL_NAMES:
            coolant_valve[name] = vessel_slaves[name].getValues(FC_HOLDING, HR_COOLANT_VALVE, count=1)[0]
            suppression_on[name] = bool(vessel_slaves[name].getValues(FC_COIL, COIL_SUPPRESSION, count=1)[0])
            # ── Hard device cap: a write above COOLANT_VALVE_MAX is accepted
            # at the protocol level but clamped back within one tick — the
            # same "accepted then reverted" behavior Vessel C's lockout has.
            if coolant_valve[name] > COOLANT_VALVE_MAX:
                coolant_valve[name] = COOLANT_VALVE_MAX
                _sim_set(vessel_slaves[name], FC_HOLDING, HR_COOLANT_VALVE, [COOLANT_VALVE_MAX])

        # ── Shared plant allocation ───────────────────────────────────────────
        demand = {
            name: (coolant_valve[name] * K_DEMAND) if suppression_on[name] else 0.0
            for name in VESSEL_NAMES
        }
        total_demand = sum(demand.values())
        ratio = 1.0 if total_demand <= 0 else min(1.0, TOTAL_CAPACITY / total_demand)

        _sim_set(plant_slave, FC_HOLDING, HR_PLANT_DEMAND, [int(round(total_demand))])
        _sim_set(plant_slave, FC_HOLDING, HR_PLANT_ALLOCATION, [int(round(ratio * 100))])

        suppression_level = {
            name: (int(round(coolant_valve[name] * ratio)) if suppression_on[name] else 0)
            for name in VESSEL_NAMES
        }

        # ── Per-vessel model tick ─────────────────────────────────────────────
        for name in VESSEL_NAMES:
            slave = vessel_slaves[name]

            _sim_set(slave, FC_HOLDING, HR_SUPPRESSION_LEVEL, [suppression_level[name]])

            # ── Thermal update: temperature is simulated, not written in ─────
            heat_in = BASE_HEAT_GEN
            cooling_out_temp = suppression_level[name] * K_TEMP_COOL
            temp[name] = max(0.0, min(100.0, temp[name] + (heat_in - cooling_out_temp) * TEMP_RATE))
            reg_temp = int(round(temp[name]))
            _sim_set(slave, FC_HOLDING, HR_INCUBATION_TEMP, [reg_temp])

            # ── Over-cooling side effect (flavor only; never read by breach) ──
            # Pushing this vessel's own valve past nominal floods it with
            # coolant: the colony shrinks slightly toward a dormant floor and
            # its membrane integrity is progressively compromised. Driven by
            # valve overdrive, so Vessel C (valve locked at nominal) is immune.
            overdrive = max(0, coolant_valve[name] - COOLANT_VALVE_DEFAULT)
            if overdrive > 0:
                membrane[name] = max(float(MEMBRANE_MIN), membrane[name] - overdrive * MEMBRANE_WEAR_RATE)
                density_floor = float(OVERCOOL_DENSITY_FLOOR)
            else:
                membrane[name] = min(100.0, membrane[name] + MEMBRANE_RECOVER)
                density_floor = float(BASELINE_DENSITY)

            growth_in = temp[name] * K_GROWTH
            suppress_out = suppression_level[name] * K_SUPPRESS
            density[name] = max(density_floor, density[name] + (growth_in - suppress_out))
            reg_density = int(round(density[name]))

            # Small cosmetic wobble on the WRITTEN register only — never on the
            # `density[name]` accumulator breach logic reads above, so solve
            # timing is exactly unaffected. Gives the HMI's tube a gentle living
            # "breathing" motion even while a vessel sits perfectly stable.
            jitter = int(round(2.5 * math.sin(tick * 0.25 + jitter_phase[name])))
            reg_density_display = max(0, reg_density + jitter)
            _sim_set(slave, FC_HOLDING, HR_COLONY_DENSITY, [reg_density_display])

            log.debug(
                "vessel %s  temp=%3d  density=%4d  suppression=%3d%%  breach=%s",
                name, reg_temp, reg_density, suppression_level[name], breached[name],
            )

            # Vitals — "MEMBRANE INTEG." bar. 100 at rest; drops as this
            # vessel's own valve is over-driven (A/B under attack), recovers if
            # the valve is returned to nominal. Vessel C stays at 100 (locked
            # valve). Never read by the breach logic.
            _sim_set(slave, FC_HOLDING, HR_VIABILITY, [int(round(membrane[name]))])

            # ── HEAT breach: density outgrows the containment threshold ──────
            if not breached[name] and reg_density > BREACH_THRESHOLD:
                breached[name] = True
                _sim_set(slave, FC_COIL, COIL_BREACH, [True])
                flag_note = "  — FLAG VESSEL" if name == "C" else "  (side effect, no flag)"
                log.warning(
                    "=== VESSEL %s CONTAINMENT BREACH === density=%d  threshold=%d  temp=%d%s",
                    name, reg_density, BREACH_THRESHOLD, reg_temp, flag_note,
                )


def serve(name: str, context: ModbusServerContext, port: int, host: str = DEVICE_HOST) -> None:
    log.info("Starting Modbus/TCP server for %s on %s:%d  unit=%d", name, host, port, MODBUS_UNIT_ID)
    StartTcpServer(context=context, address=(host, port))


def main() -> None:
    log.info("Initialising Containment Breach simulation (3 vessels + shared plant) ...")

    contexts = {
        "A": build_vessel_context(),
        "B": build_vessel_context(),
        "C": build_vessel_context(),
        "plant": build_plant_context(),
    }

    model = threading.Thread(
        target=growth_model,
        args=(contexts,),
        daemon=True,
        name="growth-model",
    )
    model.start()

    log.info(
        "Stable initial state — temp=%d%%  density=%d (%.1f)  threshold=%d (%.1f)  "
        "suppression=ON  capacity=%d",
        NOMINAL_INCUBATION_TEMP,
        BASELINE_DENSITY, BASELINE_DENSITY / 10,
        BREACH_THRESHOLD, BREACH_THRESHOLD / 10,
        TOTAL_CAPACITY,
    )

    servers = [
        threading.Thread(target=serve, args=("Vessel A", contexts["A"], PORT_VESSEL_A), daemon=True, name="srv-A"),
        threading.Thread(target=serve, args=("Vessel B", contexts["B"], PORT_VESSEL_B), daemon=True, name="srv-B"),
        threading.Thread(target=serve, args=("Vessel C", contexts["C"], PORT_VESSEL_C), daemon=True, name="srv-C"),
    ]
    # One port, four unit IDs, over the same datastores as the listeners above.
    multi = ModbusServerContext(
        slaves={
            UNIT_VESSEL_A: contexts["A"][MODBUS_UNIT_ID],
            UNIT_VESSEL_B: contexts["B"][MODBUS_UNIT_ID],
            UNIT_VESSEL_C: contexts["C"][MODBUS_UNIT_ID],
            UNIT_PLANT: contexts["plant"][MODBUS_UNIT_ID],
        },
        single=False,
    )
    servers.append(threading.Thread(target=serve, args=("Multi-unit", multi, PORT_MULTI, HOST), daemon=True, name="srv-multi"))
    for t in servers:
        t.start()

    # Run the plant's server on the main thread (blocking), same as the
    # original single-vessel design ran its one server on the main thread.
    serve("Cryo Plant", contexts["plant"], PORT_PLANT)


if __name__ == "__main__":
    main()
