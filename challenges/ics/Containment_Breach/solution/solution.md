# Containment Breach — Solution

## Status: 30%/100%-cap rebalance, verified end-to-end 2026-11-02

This is the fourth full design pass on this challenge. History, briefly:
1. **Single vessel** — two flat exploit paths (suppression-kill, overfeed), either
   popped the flag directly.
2. **Three vessels + shared plant** — A/B overheated to starve C's cooling.
3. **Thermal-runaway rework** — A/B are attacked via their own *cooling* valve,
   not heat. Temperature became a live simulated state for every vessel, and
   the valve had no real cap (nominal 100%, attack pushed to 300%).
4. **Current** — the HMI read as "100% (valve 100%)" on every vessel, which
   looked already-maxed rather than inviting "open it more." Rebalanced so the
   valve nominally sits throttled at 30% and the device genuinely hard-caps
   writes at 100% — the solve path is now "open the valve up toward the
   displayed ceiling," not "push past a number the HMI implies is already the
   max." The thermal/growth constants were rescaled so 30%-valve is the new
   zero-drift equilibrium, and the old over-100%-cooling "cryogenic lockup"
   side-breach on A/B is gone — it's no longer physically possible once actual
   received cooling can never exceed a vessel's own (capped) request.

Modbus bio-containment complex: three culture vessels (A, B, C) share one finite
cryo-suppression plant. Each vessel's `incubation_temp` is simulation output, not
an input — it drifts live based on a constant metabolic heat load versus the
cooling it actually receives, and colony growth is driven by that live
temperature. Vessel C, the flag vessel, is hardened: a local Hand-Off-Auto
lockout force-reverts any remote write to its coolant valve or suppression coil
within one tick. The only way to breach it is to starve the **shared** plant
capacity by overdriving A and/or B.

## Endpoints

| Endpoint | Unit ID (port 5030) | Role |
|----------|------|------|
| Vessel A | 1 | directly attackable |
| Vessel B | 2 | directly attackable |
| Vessel C | 3 | hardened — flag vessel |
| Cryo Plant | 4 | read-only telemetry |

## Register layout

Identical on Vessel A/B/C: `40001 incubation_temp` (R — **live simulated state**,
not writable in any lasting sense), `40002 colony_density` (R, x10 scale), `40003
breach_threshold` (R, static 1200 = 120.0), `40004 suppression_level` (R — actual
received cooling, 0-100), `40005 coolant_valve_pct` (R/W — attacker's real
lever, nominal 30%, device hard-caps writes at 100). Coil `00001
suppression_system` (R/W), `00002 breach` (R, undocumented). Cryo Plant
(read-only): `40001 total_capacity`, `40002 total_demand`, `40003
allocation_pct`.

(A sixth register, `viability_pct`, exists for HMI vitals display only — not part
of the register map handed to contestants, see "HMI-only telemetry" below.)

## The mechanics

### 1. Shared plant allocation, now with a real device cap

Each vessel with `suppression_system` ON demands `coolant_valve_pct * K_DEMAND`
(`K_DEMAND = 1.0`) units of cooling per tick. Every write to `coolant_valve_pct`
is hard-capped at `COOLANT_VALVE_MAX = 100` — a value above that is accepted at
the protocol level but clamped back within one tick, the same "accepted then
reverted" behavior Vessel C's HOA lockout already has. The plant has a fixed
`TOTAL_CAPACITY = 90` — exactly nominal 3-vessel demand at the new 30% nominal
valve, zero headroom. Every tick:

```
total_demand = sum(valve_pct_i for vessel i with suppression ON)   (each valve_pct_i <= 100)
ratio = min(1.0, 90 / total_demand)
suppression_level_i = round(valve_pct_i * ratio)   (per ON vessel; 0 if OFF)
```

Because `ratio <= 1.0` always and `valve_pct_i <= 100` always, `suppression_level_i`
can **never exceed a vessel's own valve request** — a vessel can only ever be
throttled relative to what it asked for, never over-cooled past it. Pushing
your own valve up increases your own demand on the shared pool, which shrinks
everyone else's share instead.

### 2. Live thermal state

```
heat_in     = BASE_HEAT_GEN (12, constant per vessel per tick)
cooling_out = suppression_level * K_TEMP_COOL (0.4)
temp       += (heat_in - cooling_out) * TEMP_RATE (0.06)      [clamped 0-100]
growth_in   = temp * K_GROWTH (0.6)
suppress_out = suppression_level * K_SUPPRESS (1.0)
density     += growth_in - suppress_out                        [clamped at baseline]
```

Tuned so nominal (`suppression_level = 30%`, the throttled default) is a true
equilibrium: `heat_in (12) = cooling_out (30 x 0.4 = 12)`, net zero, temperature
sits flat at 40% forever unless suppression actually changes. `TEMP_RATE`
throttles how fast temperature actually moves (thermal inertia) so the
rise/fall is visibly watchable over several seconds rather than snapping to the
clamp instantly.

This is a genuine thermal-runaway feedback loop: starving a vessel of cooling
doesn't just stop cooling — it lets temperature climb, which directly
accelerates that same vessel's own reproduction rate (since `growth_in` uses
the live `temp`), which keeps climbing as long as cooling stays starved. The
register is overwritten with the freshly computed temperature every tick, so a
direct write to it (the old "overfeed" technique) has no lasting effect on any
vessel — it's visibly reverted within ~1 tick.

### 3. One breach condition

**HEAT**: `colony_density > breach_threshold`. This is the flag condition on
Vessel C. Pushing A/B's valves up only ever *increases* their own received
cooling relative to nominal (never decreases it), so A/B cannot breach this
way themselves — they just drift a little cooler and sit dormant. Only Vessel
C, whose own valve never moves, gets starved by the shrinking shared ratio and
heats up. (The old over-100%-cooling "cryogenic lockup" side-breach on A/B no
longer exists — it required a vessel's actual received cooling to exceed its
own valve request, which is now structurally impossible under the hard cap.)

### 4. Worked numbers — the actual overload path

Push Vessel A and/or B's `coolant_valve_pct` up to the device's cap, 100
(C stays locked at nominal 30):

```
total_demand = 100 + 100 + 30 = 230  ->  ratio = 90/230 ~ 0.3913
A/B actual cooling = round(100 x 0.3913) ~ 39%   (MORE than their nominal 30% -> harmless)
C's actual cooling  = round(30  x 0.3913) ~ 12%   (LESS than nominal 30% -> starved)
```

**A/B** (own heat_in=12 constant, suppression=39%): `cooling_out = 39 x 0.4 =
15.6`, net = -3.6, scaled by `TEMP_RATE` = -0.22/tick — temperature drifts down
slowly; density stays clamped at baseline the whole time. Never breaches — this
is a harmless side effect now, not a dramatic freeze.

**C** (own heat_in=12 constant, suppression=12%): `cooling_out = 12 x 0.4 =
4.8`, net = +7.2, scaled = +0.43/tick — temperature visibly climbs from 40%.
Because `growth_in = temp * 0.6` uses that live, climbing value, C's own net
growth rate accelerates the whole way rather than growing at a flat rate.
**Live-verified result: breaches in ~25.5s**, temperature climbing from 40% to
~62% along the way (slower than the previous design's ~8-9s, since `K_GROWTH`
was rescaled down from 2.0 to 0.6 to fit the new 30%-nominal equilibrium — see
Known Issues if this ever needs retuning).

## Solve Script

```bash
pip install -r solution/requirements.txt
python solution/solve.py --path plant-overload
```

Writes `coolant_valve_pct = 100` (the device's cap) to Vessel A and B, then
polls Vessel C's density/breach coil and the plant's live allocation. Also
supports `--path direct --vessel a|b` — kills that vessel's own suppression
coil, letting its unchecked metabolic heat alone drive its own temperature up
until it breaches itself from HEAT (flavor only, no flag). The old `--mode
overfeed` (direct temperature write) technique has been removed — it no
longer does anything.

Verified live: ran `solve.py --path plant-overload` from a clean restart,
recovered the exact flag in ~25.5s, temperature and net-rate climb matching
the worked numbers above; confirmed A/B sat dormant at baseline density the
whole time (never breached). Also ran `solve.py --path direct --vessel a` —
confirmed the unaffected direct-HEAT self-breach path still works. Confirmed
directly over Modbus: a write of 300 to a vessel's `coolant_valve_pct` reads
back unclamped for under one tick, then reads back clamped to exactly 100
after; a write to Vessel C's `coolant_valve_pct` or `suppression_system`
reverts within ~1s; nominal state (no attacker input) holds perfectly flat
across 8+ ticks with zero drift (`coolant_valve_pct=30`, `suppression_level=30`,
`incubation_temp=40` on all three vessels).

## Flag

`flag{freeze_the_others_feed_the_founder}` — unchanged across all three design
passes; only the mechanism has changed, not the flag string.

## HMI (as built)

Warm/amber industrial HMI chrome (ISA-101-flavored), monospace readouts. Each
vessel is a culture vessel whose fill height is `colony_density /
breach_threshold` — consistently "amount in the tank" across all three
vessels, so a nearly-full red tube reads as "about to explode" the same way
regardless of which vessel you're looking at. A's and B's tubes stay
low/green under the intended attack (they're over-cooled, dormant — not
growing, not exploding), while C's climbs to red and overflows.

Each card also shows a **Vitals bar** ("MEMBRANE INTEG.", `viability_pct` —
now always-healthy flavor telemetry since the cold-failure mode it used to
count down from no longer exists under the hard cap), a **Status badge**
(A/B tiered on `coolant_valve_pct`: NOMINAL/DRAWN UP/MAXED; C tiered on
`colony_density`: STABLE/ELEVATED/CRITICAL), and live **Incubation Temp** and
**Metabolic Activity** readouts that genuinely move. A central "Cryo Plant"
panel shows live capacity/demand/allocation with its own progress bar.

## Verification (2026-11-02)

- Rebuilt and recreated the sim container (`docker compose build sim && docker
  compose up -d sim`) to pick up the new constants.
- Nominal equilibrium confirmed: polled all three vessels over 8 ticks (4s)
  with zero attacker input — `coolant_valve_pct=30`, `suppression_level=30`,
  `incubation_temp` flat at 40, `colony_density` flat at baseline (248-252,
  cosmetic jitter only) on every vessel. No drift.
- Confirmed the hard cap live: wrote `coolant_valve_pct=300` directly to
  Vessel A's port, read back `300` immediately, read back `100` after 1s
  (>= 1 tick) — clamp enforced exactly as designed.
- Ran `solve.py --path plant-overload` against a clean restart: recovered the
  exact flag in ~25.5s; confirmed A/B's density stayed clamped at baseline
  throughout (never breached), temp dropped to ~23-24%, suppression settled
  at 39%, valve at 100% — all matching the worked numbers.
- Ran `solve.py --path direct --vessel a` against a clean restart: confirmed
  the unaffected direct-HEAT self-breach path still works (breached in ~31s).
- Applied the rebuilt Ignition project to a live gateway (`gw.ps1 apply` +
  `gw.ps1 verify`) and confirmed visually: all three tubes consistent
  (amount-in-tank, clean CSS dome shape), A/B's badges read NOMINAL at rest,
  "Metabolic Activity" and the time-to-breach countdown correctly read
  stable/flat at nominal (fixed a stale hardcoded `K_GROWTH=2.0` in those two
  HMI expressions that had been left over from the previous design pass).
- Flag-leak check (`dist/`, `README.md`, `docker-compose.yml`, `challenge.yml`)
  clean.

## Operability

- **Expected solve time:** 15-30 minutes (discover 4 endpoints, read the
  register map, realize `incubation_temp` is read-only/live rather than a
  setpoint, realize `suppression_level` on each vessel isn't purely local,
  find the plant's capacity/demand registers, work out the overdraw).
- **Hints (progressive):**
  1. "There's more than one Modbus endpoint here."
  2. "Writing to Vessel C doesn't stick. Writing to its own temperature
     register anywhere doesn't stick either — what's the real lever?"
  3. "Check the Cryo Plant's `total_demand` against its `total_capacity`
     while A and B's coolant valves are opened up toward the cap."
- Deps pinned: `solution/requirements.txt`.
- Infra reset: `docker compose restart sim` — a few seconds, resets every
  endpoint to nominal.

## Known Issues / Notes

- `viability_pct` (HR5) is HMI-only flavor telemetry, always 100 now (the
  cold-failure condition it used to count down from no longer exists under
  the hard cap) — not part of the contestant-facing register map.
- Multi-team deployment: same open question as other live-service ICS
  challenges in this repo — one shared instance vs. per-team instancing is a
  deploy-time decision, not decided here. Each vessel's growth state is
  independent per the one running sim process; a second team hitting the same
  instance shares state with the first (no per-team isolation).
- `TEMP_RATE`/`K_GROWTH`/`BASE_HEAT_GEN` were rescaled for the new 30%-nominal
  equilibrium and empirically verified live, landing C's breach around 25s
  (up from ~8-9s in the previous design, since `K_GROWTH` dropped from 2.0 to
  0.6 to keep the same equilibrium margin at the lower nominal suppression
  level). If 25s ever feels too slow for the 15-30 min overall solve budget,
  bump `TEMP_RATE` up (e.g. toward 0.08-0.10) and re-verify live — don't trust
  hand-calculation past the first tick for this feedback loop (confirmed
  during the original tuning pass: an earlier faster `TEMP_RATE` landed the
  breach several seconds off from what the formula alone predicted, found
  only by running it).
