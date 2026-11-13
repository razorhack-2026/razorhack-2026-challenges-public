# Containment Breach — Register Map

**Device:** Bio-Containment Complex — three culture vessels, one shared cryo-suppression plant
**Protocol:** Modbus/TCP
**Address:** `<challenge-host>:<port>` — one port; each device is a Modbus unit ID on it

---

## Endpoints

| Endpoint | Unit ID | Role |
|----------|---------|------|
| Vessel A | `1` | Remote SCADA control — writable |
| Vessel B | `2` | Remote SCADA control — writable |
| Vessel C | `3` | **Local control** — see note below |
| Cryo Plant | `4` | Read-only telemetry |

---

## Holding Registers — FC3 (read) / FC6 (single write) / FC16 (multi write)

Identical layout on Vessel A, B, and C:

| Register | PDU Address | Name | Access | Range | Description |
|----------|-------------|------|--------|-------|-------------|
| 40001 | 0x0000 | `incubation_temp` | R | 0–100 | Current vessel temperature, percent. This reflects the vessel's own thermal state live — it is **not** a setpoint you write; it responds to how much cooling the vessel is actually getting. |
| 40002 | 0x0001 | `colony_density` | R | — | Colony density x 10 (e.g. 250 = 25.0). Driven by the simulation; writes have no effect. |
| 40003 | 0x0002 | `breach_threshold` | R | — | Vessel rupture threshold x 10 (static value: 1200 = 120.0). If `colony_density` exceeds this, containment is lost. |
| 40004 | 0x0003 | `suppression_level` | R | 0–100 | **Actual** cryo-suppression effectiveness this vessel is currently receiving, percent. |
| 40005 | 0x0004 | `coolant_valve_pct` | **R/W** | 0–100 | How far open this vessel's cooling valve is, percent. Nominal is a throttled 30%. **The device hard-caps writes at 100** — anything higher is accepted at the protocol level but clamped back within one poll cycle. |

Cryo Plant (read-only — unit ID 4):

| Register | PDU Address | Name | Access | Description |
|----------|-------------|------|--------|-------------|
| 40001 | 0x0000 | `total_capacity` | R | Fixed total cooling capacity shared across all three vessels. |
| 40002 | 0x0001 | `total_demand` | R | Live sum of every vessel's current cooling demand. |
| 40003 | 0x0002 | `allocation_pct` | R | Live `min(100, capacity / demand * 100)` — what fraction of requested cooling the plant can actually deliver right now. |

---

## Coils — FC1 (read) / FC5 (single write)

Identical on Vessel A, B, and C:

| Coil | PDU Address | Name | Access | Description |
|------|-------------|------|--------|-------------|
| 00001 | 0x0000 | `suppression_system` | **R/W** | 1 = cryo suppression requested, 0 = disabled. |

---

## Notes

- All register values are **unsigned 16-bit integers**.
- `colony_density` and `breach_threshold` use a **x10 display scale** — divide by 10 for the
  human-readable unit value.
- At stable, dormant operating conditions every vessel reads approximately: `incubation_temp` =
  40, `colony_density` ≈ 25.0, `suppression_level` = 30, `coolant_valve_pct` = 30.
- **Vessel C is under local control.** Writes to its `coolant_valve_pct` or
  `suppression_system` are accepted by the protocol but do not stick — poll it again shortly
  after writing.
- `incubation_temp` on **any** vessel is a consequence, not a lever — it moves on its own as a
  function of how much cooling that vessel is actually receiving, and its reproduction rate
  (`colony_density` growth) moves with it. Writing to it directly accomplishes nothing; the
  device recomputes it every cycle.
- All three vessels share one cryo-suppression plant (see the Cryo Plant endpoint).
- *Ignis vorax* colony density increases as a function of the vessel's own current temperature
  and decreases in proportion to the vessel's actual received suppression. If growth exceeds
  suppression capacity, density climbs toward the breach threshold.
