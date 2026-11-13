# Last Mile — Solution (GM only)

*(3/3 of the "Lateral Drift" sequence. Gated by **Lateral Drift** (2/3)'s engineering-workstation
access. Final part of the chain, no further hand-off.)*

**Flag:** see `../challenge.yml`. **Reference solver:** `solve.py`. **Difficulty tag:** Medium (see
"Known issues": probably Easy-Medium).

## Status: reworked 2026-11-01, verified live

History: 2026-10-22 "probe the registers blind, push the setpoint over the limit"; 2026-11-01
morning "default unlock code from the documentation"; 2026-11-01 evening (current): documentation +
default unlock code + a **rotor critical speed** the player must find and track, ending in a
**feed vessel meltdown** that shows the flag. Story: the Keeper of Tomorrow's Kalium refinery. No
animated HMI page; the controller serves a plain status page and `/api/state` JSON.

## The idea

Mission framing: by the time the player reaches the workstation they can see Rootkit has taken over this
refinery line and is enriching Kalium for himself; the objective is to stop him by destroying the centrifuge.
Line 2 of the Keeper of Tomorrow's Kalium refinery spins raw Kalium feed gas through an enrichment centrifuge (RC-200
controller). The controller ships locked with a factory-default code (documented, never changed).
Once unlocked, the player can set the rotor speed. A real rotor has a **critical speed**: at about
68 % it resonates, which shakes it, wears its bearing, and heats the bearing. A hot bearing moves
the critical speed **upward**, so a fixed setpoint walks out of the band and the wear recovers. The
player has to find the critical speed by sweeping while watching the vibration register, then
**track** it as it drifts (this is the Stuxnet-style "drive the rotor to its destruction" idea).
At 100 % wear the bearing seizes, the cascade scram relay latches, and the draw-off from the feed
vessel stops, so the vessel heats (40 C/s from 320 C). Past 1200 C: **MELTDOWN**. The flag is shown
only then, on the status page and in `/api/state`. It is never in a Modbus register.

## Intended solve

1. From Lateral Drift's workstation, open the **Documents** panel's commissioning sheet
   (`/docs/rc200-commissioning`): Modbus endpoint, full register map, the factory default unlock
   code, and an operating note that the rotor has a critical speed in its working range that moves
   as the bearing heats.
2. Write the default code to 40004. Coil 00002 goes true. (Five wrong codes lock 40004 for 60 s.)
3. Sweep the rotor speed setpoint (40001) from the nominal 45 % up to the firmware clamp (85 %) in
   small steps, reading vibration (40006). One narrow band spikes to about 15 mm/s.
4. Hold the rotor in the band. Bearing temperature (40007) and wear (40008) climb. The band drifts
   up (about +3 to +4 %), so keep re-centering on the loudest speed. A fixed hold stalls and wear
   decays back to 0.
5. At 100 % wear the scram relay latches (coil 00001) and the rotor stops. The feed vessel
   temperature (40009) climbs. After about 20 s it reaches the melt limit and the status page shows
   the flag.

## Register layout (published on the commissioning sheet)

| Register | PDU | Name | Access | Notes |
|---|---|---|---|---|
| 40001 | 0x0000 | `rotor_speed_setpoint` | R/W | 0-100, clamped to `safe_limit`; ignored while locked |
| 40002 | 0x0001 | `safe_limit` | R | static, 85 |
| 40003 | 0x0002 | `rotor_speed` | R | ramps toward the setpoint at 8 %/s |
| 40004 | 0x0003 | `maint_unlock` | W | factory default code; always reads 0 |
| 40005 | 0x0004 | `lockout_seconds` | R | seconds left on a wrong-code lockout |
| 40006 | 0x0005 | `vibration` | R | mm/s x10 |
| 40007 | 0x0006 | `bearing_temp` | R | degrees C |
| 40008 | 0x0007 | `bearing_wear` | R | 0-100 % |
| 40009 | 0x0008 | `feed_vessel_temp` | R | degrees C |
| Coil 00001 | 0x0000 | `scram_tripped` | R | latches when the rotor bearing seizes |
| Coil 00002 | 0x0001 | `maint_unlocked` | R | true once the correct code was written |

## Solve script

```bash
pip install -r solution/requirements.txt
python solution/solve.py --host <plc-host> --port <modbus-port> --status-port <status-port> \
    [--unlock-code 4087]
python solution/solve.py --skip-unlock    # GM check: the lock must hold (setpoint write ignored)
```

`solve.py` unlocks, sweeps 50-85 % in 2 % steps, then hill-climbs (probe one step either side and
move toward the louder one) until the scram latches, then polls `/api/state` for the flag. Full
run: about 1-1.5 minutes on the dev machine.

## Verified 2026-11-01

- Locked controller ignores the setpoint write; 5 wrong codes -> `lockout_seconds` = 60 and even
  the correct code is ignored until it expires; the right code unlocks.
- Full solve from a clean restart: found the critical speed at 68 %, tracked it up to about 71-72 %,
  bearing seized, the feed vessel melted down, flag recovered (several runs).
- **A fixed hold fails:** holding 68 % for 45 s took wear to about 50 % and then back to 0 as the
  band drifted away (wear threshold 6 mm/s; off-band vibration stays near 5 mm/s).
- Restart resets everything (unlock, wear, temperatures, scram, setpoint).
- The status page and `/api/state` carry no flag until the melt limit is reached.

## Operability

- **Expected solve time:** 10-20 minutes by hand (read the sheet, unlock, sweep, track), about 1-2
  minutes with a script.
- **Hints (if stuck):** 1) "The workstation has more than one panel. Look for paperwork." 2) "The
  setpoint won't move until the controller is unlocked." 3) "Something about the rotor is wrong at
  one speed. Watch the vibration register while you sweep." 4) "The sweet spot moves while you are
  in it."
- **Deps pinned:** `solution/requirements.txt` (`pymodbus==3.6.9`).
- **Infra reset:** `docker compose restart process-plc` in `../Lateral_Drift/`. A few seconds, well
  under 2 minutes. At the event each team gets its own copy (Fargate instance `lateral-drift`).

## Setup / deployment notes

**Prerequisites:** Docker + Docker Compose, Python 3.11+ with the pinned deps in
`solution/requirements.txt`.

**This PLC runs in Lateral Drift's copy.** Both challenges are one per-team Fargate task
(instance `lateral-drift`) with one network namespace, and that task's images are built from one
folder, so the PLC's source is `../Lateral_Drift/src/process_plc/` and it is started by
`../Lateral_Drift/docker-compose.yml` (`network_mode: service:vpn-gateway`). It listens on
**127.0.0.1 only** (Modbus 502, status page 8000), so the competitor reaches it solely by
tunnelling through Lateral Drift's `vpn-gateway`, and the `engineering-workstation` advertises
`127.0.0.1:502` / `http://127.0.0.1:8000/`, which the gateway resolves to this PLC. `GET /` is a
plain auto-refreshing status page; `GET /api/state` is the same data as JSON (events, phase,
temperatures).

```bash
cd ../Lateral_Drift && docker compose up -d --build
docker compose logs -f process-plc
# the competitor's path, which is also how solve.py's defaults (5020 / 8010) reach it locally:
ssh -N -L 5020:127.0.0.1:502 -L 8010:127.0.0.1:8000 rootkit@localhost -p 2223
python solution/solve.py          # from Last_Mile/, through the tunnel
```

**Tuning** (`../Lateral_Drift/src/process_plc/config.py`): `BAND_CENTER0` (68), `BAND_DRIFT_PER_C` (0.45),
`BAND_WIDTH` (2.5), `WEAR_RATE` (12 %/s), `WEAR_THRESHOLD` (6 mm/s), `HEAT`, `COOL_TAU`,
`CORE_HEAT_RATE` (40 C/s), `CORE_TEMP_MELT` (1200), `RAMP_RATE` (2 %/tick), plus the unlock
(`DEFAULT_UNLOCK_CODE` 4087, `MAX_WRONG_CODES` 5, `LOCKOUT_SECONDS` 60). The `CORE_*` constants
and the `core` field in `/api/state` are the feed vessel (kept as `core` internally).

**Keep in sync:** the unlock code and register map are also printed on Lateral Drift's commissioning
sheet (`../Lateral_Drift/src/engineering_workstation/templates/commissioning.html`, code in that service's
`config.py` as `PLC_UNLOCK_CODE`). Change them together. The flag in `challenge.yml` must equal
`FLAG` in `../Lateral_Drift/src/process_plc/config.py` (checked equal on 2026-11-01).

## Known issues / notes

- **Multi-team isolation:** a meltdown stays latched until `docker compose restart`, so a shared
  instance would be everyone's state. Decided 2026-11-05: one copy per team (Fargate instance
  `lateral-drift`, shared with Lateral Drift); Stop and Start in CTFd gives a team a fresh PLC.
- **Difficulty:** with the sheet in hand and a script, this is closer to Easy-Medium than Medium.
  Re-check the tag after a fresh-agent blind test (not run yet).
- **No animated HMI.** An earlier plan was a live control-room page. That page was not built; the
  controller serves a plain status page. A nicer front end could be added later without changing the
  simulation or the solve (everything it needs is in `/api/state`).
- **Technique overlap:** Factory Fresh also centres on a documented default login. Here it is a
  Modbus unlock code found by pivoting, and the real puzzle is the critical-speed tracking.
- `/api/state` has no auth by design (it mirrors a PLC web panel). The flag appears in it only
  after the melt limit.
- **Kalium enrichment is display-only flavor.** The `purity` field in `/api/state` and the
  "AT-201 KALIUM ENRICHMENT" faceplate on the HMI are a derived analyzer readout (raw feed 72 %
  climbing toward the 99.5 % fuel-grade target while the line runs normally; it stalls while the
  rotor is held in the resonance band and decays back toward raw feed after the scram). It is NOT
  a Modbus register (the published register map is unchanged) and has no effect on the attack, the
  flag, or the reference solver. Tunables live in `config.py` (`PURITY_*`).
