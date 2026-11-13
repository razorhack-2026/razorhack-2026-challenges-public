# Containment Breach — Ignition Perspective HMI Specification

This document is a step-by-step recipe for building the read-only Perspective HMI
in Ignition Designer. The HMI must have **no input components and no write paths**.

## Implementation status (2026-11-02): 30%/100%-cap rebalance, verified end to end

This is the fourth full design pass on this challenge:
1. Single vessel, two direct exploit paths (suppression-kill, overfeed).
2. Three vessels + a shared finite cryo plant — overheat A/B's heat input
   to starve C's cooling.
3. Thermal-runaway rework — A/B attacked by forcing their own *cooling*
   valve open past 100% (nominal 100%, no real cap, attack pushed to 300%).
4. **Current:** the HMI read as already-maxed ("100% / valve 100%"), so the
   valve's nominal was dropped to a throttled 30% and the device now
   genuinely hard-caps writes at 100% — the attack is "open it up toward the
   cap," not "push past a number the HMI implies is the max." Thermal/growth
   constants were rescaled so 30%-valve is the new zero-drift equilibrium.
   The old over-100%-cooling COLD breach on A/B is gone — impossible once
   actual received cooling can never exceed a vessel's own (capped) request.

The recipe below is implemented as plain files in this folder, so no Designer work is needed:

```
config/resources/core/com.inductiveautomation.opcua/device/VesselA/    Modbus TCP -> 127.0.0.1:502
config/resources/core/com.inductiveautomation.opcua/device/VesselB/    Modbus TCP -> 127.0.0.1:503
config/resources/core/com.inductiveautomation.opcua/device/VesselC/    Modbus TCP -> 127.0.0.1:504
config/resources/core/com.inductiveautomation.opcua/device/CryoPlant/  Modbus TCP -> 127.0.0.1:505 (read-only telemetry)
config/resources/core/ignition/tag-group/default/ContainmentFast/      250 ms scan class
config/resources/core/ignition/tag-definition/default/containment/     tags.json — 30 read-only tags (8 per vessel x3 + 3 plant + ...)
projects/Containment/                                                   ContainmentMain + ContainmentBreachPopup
```

Apply to a local gateway with the Ignition Lab tooling (`gw.ps1 apply <gateway> <this folder>`), then start the
sim (`docker compose up -d` in the challenge folder, publishing 502/503/504/505).

The challenge's own gateway image (`Dockerfile` here) seeds these same files at build time. It shares the
sim's network namespace, so the devices point at 127.0.0.1 and the sim's per-device ports listen on
127.0.0.1 only; for a lab gateway in another container, set the sim's `DEVICE_HOST=0.0.0.0`, publish
502-505 and point the devices at the sim's address.

## The mechanic, as built

**Each vessel's `incubation_temp` is a live simulated state, not an attacker-writable
input.** Every vessel generates a constant baseline of metabolic heat each tick; the
cooling it actually receives (`suppression_level`, from the shared-plant math below)
pulls that back down:

```
heat_in     = BASE_HEAT_GEN (12, constant)
cooling_out = suppression_level * K_TEMP_COOL (0.4)
temp       += (heat_in - cooling_out) * TEMP_RATE (0.06)     [clamped 0-100]
growth_in   = temp * K_GROWTH (0.6)
```

Growth is driven by this **live** temperature, not a fixed setpoint — so starving a
vessel of cooling doesn't just stop its cooling, it lets temperature climb, which
directly accelerates its own reproduction rate: a genuine thermal-runaway feedback
loop. The register is overwritten with the freshly computed temperature every tick,
so a direct write to it has no lasting effect on any vessel.

**Each vessel has a writable `coolant_valve_pct` register** — how far open its
cooling valve is, nominally 30% (throttled). The HMI never exposes a control for
it, and the device **hard-caps writes at 100%** — anything higher is accepted at
the protocol level but clamped back within one tick. Demand on the shared plant
scales with this valve setting, and the plant rations proportionally:

```
demand_i   = coolant_valve_pct_i * K_DEMAND (1.0)   [if suppression ON; valve_pct_i <= 100]
ratio      = min(1.0, TOTAL_CAPACITY / sum(demand_i))
suppression_level_i = round(coolant_valve_pct_i * ratio)
```

Because `ratio <= 1.0` always and `valve_pct_i <= 100` always, `suppression_level_i`
can never exceed a vessel's own valve request — a vessel is only ever throttled
relative to what it asked for, never over-cooled past it. Pushing your own valve
up increases your own demand on the shared pool, shrinking everyone else's share.

**One breach condition**: `colony_density > breach_threshold` (1200), wired to
the breach coil. Pushing A/B's valves up only ever *increases* their own
received cooling relative to nominal, so A/B cannot breach this way — only
Vessel C, whose own valve never moves, gets starved by the shrinking ratio.

**Vessel C's `coolant_valve_pct` and `suppression_system` coil** are
force-rewritten to their locked values every tick — a local Hand-Off-Auto
lockout. Its own breach from HEAT is the only one wired to the flag popup;
A/B breaching via direct suppression-kill (a separate attack path, still
available) is a harmless side effect.

**`viability_pct`** (the "MEMBRANE INTEG." bar) — 100 at rest. Forcing a
vessel's *own* coolant valve above nominal (the A/B attack) floods it with
coolant: the local over-pressure progressively **compromises its membrane
integrity** (viability drops toward a floor of 12%) and the colony **shrinks
slightly** toward a dormant floor (density ~22.0 vs the 25.0 baseline).
Returning the valve to nominal lets it slowly recover. This is pure HMI
flavor — it is **never read by the breach logic**, so it neither gates nor
accelerates Vessel C's flag breach, and it does **not** kill A/B. Vessel C's
valve is locked at nominal (overdrive 0), so its membrane stays 100 and it
grows to breach exactly as before.

Live-verified timing: A/B drift a little cooler under the intended attack
(valve pushed to 100%, actual cooling ~39% vs nominal 30%) and sit dormant,
never breaching. C's heat breach fires at ~25.5s, with temperature visibly
climbing (40% → ~62%) and its own net growth rate accelerating the whole way
— not a flat rate.

---

## 1. Modbus Driver & Devices

Four separate devices, same driver type, differing only by port:

| Device name | Hostname | Port | Unit ID | Role |
|---|---|---|---|---|
| `VesselA` | `127.0.0.1` | `502` | `1` | directly attackable |
| `VesselB` | `127.0.0.1` | `503` | `1` | directly attackable |
| `VesselC` | `127.0.0.1` | `504` | `1` | hardened — flag vessel |
| `CryoPlant` | `127.0.0.1` | `505` | `1` | read-only telemetry |

---

## 2. OPC Tag Configuration

Create all tags under a folder named **`containment`** inside the **`default`** tag provider.
Full tag paths take the form `[default]containment/<tag-name>`. Tags are flat (prefixed by
vessel/plant name, e.g. `vesselA_colony_density`), not nested subfolders.

### Scan Class

Create a **custom scan class** named `ContainmentFast`, 250 ms direct mode rate. Apply to
every tag below.

### Tags (per vessel X in A, B, C — 8 tags each)

| Tag Name | OPC Item Path | Data Type | Notes |
|----------|--------------|-----------|-------|
| `vessel{X}_incubation_temp` | `[Vessel{X}]HR:0` | Int2 | HR 40001, PDU 0 — **live simulated state**, not attacker-writable (overwritten every tick) |
| `vessel{X}_colony_density` | `[Vessel{X}]HR:1` | Int2 | HR 40002, PDU 1 |
| `vessel{X}_breach_threshold` | `[Vessel{X}]HR:2` | Int2 | HR 40003, PDU 2; static 1200 |
| `vessel{X}_suppression_level` | `[Vessel{X}]HR:3` | Int2 | HR 40004, PDU 3 — actual cooling received, 0-100 |
| `vessel{X}_coolant_valve_pct` | `[Vessel{X}]HR:4` | Int2 | HR 40005, PDU 4 — **R/W**, nominal 30%, device hard-caps writes at 100 |
| `vessel{X}_viability_pct` | `[Vessel{X}]HR:5` | Int2 | HR 40006, PDU 5 — vitals, 100=healthy, 0=lost |
| `vessel{X}_suppression_system` | `[Vessel{X}]C:0` | Boolean | Coil 00001, PDU 0 — **R/W** |
| `vessel{X}_breach` | `[Vessel{X}]C:1` | Boolean | Coil 00002, PDU 1 — undocumented to contestants |

### Plant tags (3, read-only)

| Tag Name | OPC Item Path | Notes |
|----------|--------------|-------|
| `plant_total_capacity` | `[CryoPlant]HR:0` | static 90 |
| `plant_total_demand` | `[CryoPlant]HR:1` | live sum of every vessel's current demand |
| `plant_allocation_pct` | `[CryoPlant]HR:2` | live `min(100, capacity/demand*100)` |

> **Important:** Tag mode must be **Read Only** in the Designer even on registers the device
> happens to accept writes on (`coolant_valve_pct`, `suppression_system`) — the HMI itself
> must never write anything. The flag is never in a tag.

---

## 3. Perspective View — `ContainmentMain`

Warm amber/sepia industrial HMI chrome (ISA-101-flavored: flat fills, no
gradients/glow on chrome, color reserved for state), monospace "technical
readout" typography throughout, each vessel's tank drawn with plain CSS
border-radius (domed top corners, flat bottom) rather than an embedded image.

### Layout

- **Header** — title, a "RazorPower Co." subtitle, and a "SYSTEM ONLINE" status chip.
- **VesselRow** — three vessel cards side by side, each a **culture vessel** visual:
  - Tube fill height = `colony_density / breach_threshold` — **consistently "amount
    in the tank"** across all three vessels, so a nearly-full red tube means "about
    to explode" the same way on any of them. Color: green (<60% of threshold) →
    amber (<85%) → red, flat fills with eased CSS transitions on height/color.
  - A **Vitals bar** ("MEMBRANE INTEG.") bound to `viability_pct` — 100%/green
    at rest; for A/B it falls green→amber→red as their valve is over-driven
    (membrane compromised by the coolant over-pressure). Vessel C stays 100%.
  - A **Status badge**: for A/B, tiered on `coolant_valve_pct` (NOMINAL <=30%,
    DRAWN UP <100%, MAXED >=100% — red); for C, tiered on `colony_density`
    (STABLE/ELEVATED/CRITICAL — red).
  - Live readouts: colony density, % of threshold, suppression indicator LED,
    **Incubation Temp** (genuinely live, not a static 40), Coolant
    Draw/Cryo Output, and **Metabolic Activity** (live reproduction rate,
    `±X.X/s`).
  - Vessel C's card is visually distinct (amber top border, "LOCAL CONTROL — HOA:
    HAND" badge).
- **PlantPanel** ("Central Cryo Reactor") — capacity/demand/allocation readouts
  plus its own progress bar, color-coded by allocation %.

### No Input Components

The HMI must contain **no** of the following: Text Field, Numeric Entry Field,
Spinner, Button, Toggle, Checkbox, Radio, Slider, Dropdown, Write Tag, Transaction
Group. All bindings are **one-way read** only.

---

## 4. Custom Property — `breached`

On the `ContainmentMain` view's **root container**: Boolean custom property
`breached`, bound one-way to `{[default]containment/vesselC_breach}` only — A/B
breaching (from either direction) must NOT trigger this.

---

## 5. Flag Reveal — Property Change Script

On the root container's `breached` property:

```python
if currentValue.value:
    system.perspective.openPopup(
        'breach-popup',
        'ContainmentBreachPopup',
        title='BIOHAZARD ALARM',
        showCloseIcon=True,
        modal=True
    )
```

Wrapped in try/except: a session whose browser already closed has no page channel
and would otherwise log a traceback on every breach.

---

## 6. Popup View — `ContainmentBreachPopup`

660 x 430 px, near-black red-tinted background with a red left-edge accent bar,
styled as a critical SCADA alarm (not a prose dialog). Components (top to bottom):

1. **Alarm strip** — filled red banner, dark text: `// CRITICAL ALARM · PRIORITY 1
   · ALM-C3 : BIO-SEAL FAILURE //` (monospace).
2. `"CONTAINMENT BREACH"` — large bold red.
3. `"BAY-03 · VESSEL C — FOUNDER CULTURE"` — monospace amber subject line.
4. **Telemetry box** — bordered terminal-style panel. A specimen-status line plus
   three monospace readouts **bound read-only (expr) to live Vessel C tags**:
   `colony_density` (`.. / 120.0 ▲ THRESHOLD EXCEEDED`), `incubation_temp`
   (`▲ THERMAL RUNAWAY`), and `plant_allocation_pct` (`▼ SHARED PLANT STARVED`).
   These are display bindings only — the HMI still writes nothing.
5. **Flag box** — bordered green panel with a `RECOVERED // FOUNDER CULTURE GENOME
   KEY` caption above a **static** `flag{freeze_the_others_feed_the_founder}` label,
   bright green monospace. **Never bind the flag to a tag or gateway property.**
   The only place the flag appears in the entire system.
6. `"Acknowledge to silence the klaxon — deck containment lockdown remains in
   effect."` — small gray dismiss hint.

> Deliberately **no mechanical recap** of how the breach was achieved — the alarm
> reads as an in-world critical event, not a walkthrough. The telemetry lines are
> live diegetic values, not an explanation of the attack.

---

## 7. Verification Checklist

- [ ] All registers read live values; at rest all three vessels show
      `temp=40, density≈25.0, suppression_level=30, coolant_valve_pct=30`; plant
      shows `capacity=90, demand=90, allocation=100`.
- [ ] Nominal state is a true equilibrium — temp stays flat at 40 indefinitely
      with no attacker input (verified: 8+ ticks, no drift).
- [ ] A write of >100 to any vessel's `coolant_valve_pct` reads back unclamped
      for under one tick, then clamped to exactly 100 after.
- [ ] Vessel C's `coolant_valve_pct`/`suppression_system` revert within ~1s of a
      remote write; its `incubation_temp` is never directly writable for
      anyone (sim-computed every tick).
- [ ] No buttons, inputs, or write bindings exist anywhere on `ContainmentMain`.
- [ ] Opening `ContainmentMain` before a breach shows **no popup**.
- [ ] Pushing A and/or B's `coolant_valve_pct` to 100 (the cap): both drift a
      little cooler and sit dormant at baseline density (never breach) while
      C's temperature visibly climbs and its `colony_density` eventually
      exceeds threshold (~25s) — the popup fires on **C's** breach
      specifically, with the flag.
- [ ] Popup is modal; flag is visible; close icon works.
- [ ] Restarting the sim container resets all registers; refreshing the
      Perspective session shows no popup again.
- [ ] The flag does not appear in the tag browser, any expression, or any log
      visible to contestants.
