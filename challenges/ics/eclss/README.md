# ECLSS: Training Bay and the ISV Ozark Horizon

**Category:** ICS
**Difficulty:** Easy to Hard (per challenge, below)
**Author:** Anon

## Description (what the competitor will see)

The ISV Ozark Horizon's life-support system has turned on its crew. Before you
touch the ship, the **Training Bay** walks you through the three tools it runs
on: **Modbus**, **OpenPLC** logic, and an **Ignition** HMI. Then the **ECLSS**
challenge puts them together. Oxygen is sagging, CO2 is climbing, the cabin is
running hot, and something keeps undoing every fix you make.

Twenty-two challenges in two parts. Do the Training Bay first; every skill it
teaches comes back on the ship.

| Part | Challenges | Difficulty | Where |
|------|-----------|------------|-------|
| Training Bay, Modbus | MB1 Roll Call, MB2 Long Read, MB3 The Vendor Manual, MB4 Light the Beacon | Easy | Training PLC, Modbus/TCP |
| Training Bay, Modbus | MB5 Big Number, MB6 Floating Point, MB7 Breaker Panel | Medium | Training PLC, Modbus/TCP |
| Training Bay, OpenPLC | PL2 Hold to Confirm | Easy | Training PLC, Modbus/TCP |
| Training Bay, OpenPLC | PL1 Airlock Cycle, PL4 Motor Starter, PL5 Four to Twenty | Medium | Training PLC, Modbus/TCP |
| Training Bay, OpenPLC | PL3 Count the Pulses | Hard | Training PLC, Modbus/TCP |
| Training Bay, Ignition | IG1 Who Are You?, IG2 Hidden in Plain Sight | Easy | Ignition gateway |
| Training Bay, Ignition | IG3 Tune the Beacon | Medium | Training HMI |
| ECLSS | 1 Hailing frequencies, 2 The ghost deck | Easy | Ship PLC, ship HMI |
| ECLSS | 3 Breathe easy, 4 Scrub it out, 5 Goldilocks | Medium | Ship PLC |
| ECLSS | 6 Exorcise the maintenance sync, 7 All systems nominal | Hard | Ship PLC and HMI |

**Targets.** Your team gets its own copy of the whole rig. Press **Start** on
any of these challenges; its connection info then shows your copy's host. A
fresh copy takes a few minutes to come up, and **Stop** resets everything.

- Training Bay PLC: Modbus/TCP port 5020, unit id 1
- Ship (ECLSS) PLC: Modbus/TCP port 502, unit id 1
- Ignition gateway: `http://<host>:8088`. The Training HMI is at
  `/data/perspective/client/training` and the ship HMI is at
  `/data/perspective/client/eclss`

Use any Modbus client (mbpoll, pymodbus, a Metasploit module, your own script)
and a web browser. Everything you need is on those services. Don't hammer the
PLCs with thousands of writes per second. You won't need to, and it slows
the rig down.

## Files Provided

- `dist/MODBUS_PRIMER.md`: Modbus in 10 minutes, for players new to OT
- `dist/training/TRAINING_GUIDE.md`: the Training Bay briefings
- `dist/training/REGISTER_MAP.md`: the Training Bay PLC's register map
- `dist/training/TRAINING_LOGIC.st`: the Training Bay PLC's Structured Text source, with secret constants redacted
- `dist/eclss/CHALLENGES.md`: the ECLSS crew briefing
- `dist/eclss/REGISTER_MAP_PLAYER.md`: the ship's flight-deck register map (telemetry, setpoints, commands; not complete)

*Gamemasters: deploy and verify notes are in `solution/README.md`.*
