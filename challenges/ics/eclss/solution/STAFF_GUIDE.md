# RazorHack ICS - Staff Guide: Training Bay & ECLSS Challenge

Nov 2, 2026 · Anon

**Staff only - contains every solution and flag.** RazorHack ICS has two parts worth 1000 points each: a 15-challenge **Training Bay** that teaches Modbus, OpenPLC logic and Ignition, and the 7-flag **ECLSS challenge**, a sabotaged spaceship life-support system that uses all three skills at once.

## Overview

Each team gets its own copy of the rig: two OpenPLC v4 runtimes (one per part) and one Ignition 8.3 gateway that hosts both HMIs, run as one Fargate task started from CTFd (`instance:eclss`). Players attack only two services - Modbus TCP on the PLCs and the Ignition web pages - from their team's Kali box. Hosting, deploy and health checks: `README.md` next to this guide.

| Part | Target | Address | Challenges | Points |
| --- | --- | --- | --- | --- |
| Training Bay | OpenPLC (training program) | `tcp://<host>:5020` | MB1-MB7, PL1-PL5 | 825 |
| Training Bay | Ignition Training HMI | `http://<host>:8088/data/perspective/client/training` | IG1-IG3 | 175 |
| ECLSS | OpenPLC (ECLSS program) | `tcp://<host>:502` | Flags 1, 3-7 | 825 |
| ECLSS | Ignition ECLSS HMI | `http://<host>:8088/data/perspective/client/eclss` | Flags 2, 6 | 175 |

**Hand to players** (in `../dist/`): `eclss/CHALLENGES.md` (ECLSS briefing), `MODBUS_PRIMER.md`, and `training/` (briefing, register map, PLC source with secrets redacted). **Keep for staff:** this guide, `eclss/HINTS.md`, `training/HINTS.md`, and `../src/build/training/flags_all.json`.

The intended path is Training Bay first (about 1-2 hours for an intermediate undergraduate team), then the ECLSS challenge. Every ECLSS skill is rehearsed in the Training Bay: reading and writing registers, decoding packed text, reading PLC logic, and pivoting from an HMI page to a PLC write.

## Setup, verification and reset

The rig is three images (`../src/images/`) with everything baked in: both PLC programs compiled and set to run, and the gateway with both HMIs, both Modbus devices and every tag. There is no provisioning step, no Designer and no Script Console. Deploy, health checks and changing flags are in `README.md` next to this guide; local testing is `docker compose up -d --build` in `../src/`.

1. **Set event flags (optional).** Edit `flags.json` (ECLSS) and `training/training_flags.json`. Flags use the `flag{...}` format and must be 32 ASCII characters or fewer; the builder refuses longer ones.
2. **Build.** `docker compose run --rm builder` compiles both PLC programs with STruC++ v0.7.0 and runs all 35 unit tests (15 ECLSS, 20 Training); every test must pass. The repo ships programs prebuilt from the default flags, so this step is required only after editing flags. The OpenPLC v4 runtime only accepts this compiled form, never raw Structured Text.
3. **Build and push the images**, then start a copy as team 00 from CTFd (`README.md`).
4. **Check the HMIs.** `/data/perspective/client/eclss`: the MET clock in the header ticks every second and the three gauges move. `/data/perspective/client/training`: the beacon console loads and the PLC link heartbeat is live.
5. **Health checks.** `solve.py` ("rig is healthy", up to \~4 min) and `solve_training.py --gateway ...` ("rig healthy"). Both print every flag they capture as `flag{...}`.
6. **Reset after the health checks** - the solvers really do solve everything. Stop and Start the copy.

**Reset.** Every Start is a fresh copy: a new ship (MaintSync re-armed, flags 3-7 unpublished) and a fresh Training Bay. Teams reset their own copy with Stop and Start.

**OpenPLC runtime APIs.** Each runtime's REST API (8443 for ECLSS, 8444 for Training) listens on `127.0.0.1` inside the copy only: anyone who can log in can upload a program or download the running one, and its source contains every flag and the disarm code. Nothing needs it at run time; the programs are compiled in when the images are built (`../src/images/plc/bake.sh`).

## How flags work

Every flag is `flag{...}`, and the PLC only publishes a gated flag while (or after) the player has actually produced the condition it rewards - reading the source code or the register map alone never reveals one.

**Text flags in registers.** The PLC stores flag text in a block of 16 holding registers, two ASCII characters per 16-bit register, low byte first. That is why every flag is limited to 32 characters, and why the first register of every flag reads **27750** (`0x6C66`, bytes `f` then `l`). Decoding:

```
b = bytearray()
for v in regs:
    b += bytes([v & 0xFF, (v >> 8) & 0xFF])
print(b.split(b"\x00")[0].decode())
```

**Gated vs. always readable.** Recon flags (Training MB2, MB3; ECLSS flag 1) are always present. Every other Modbus flag reads as zeros until the PLC sets that challenge's bit in a status word: `FlagsEarned` (HR14) on the ECLSS PLC, `Unlock_Word` (HR745) on the training PLC.

**Derived flags.** Four Training flags are not stored as text; the answer itself is the flag: MB1 `flag{<bay id>}`, MB5 `flag{<32-bit value>}`, MB6 `flag{<float to 3 decimals>}`, and IG1 `flag{<gateway name>}`.

**HMI-only flags.** ECLSS flag 2, Training IG2 and IG3 live in Ignition view text (ECLSS flag 6 is Modbus only: `/maint` gives the code, not the flag). IG3's text sits inside an expression binding evaluated on the gateway, so the browser only ever receives it once the PLC confirms the lock.

**Success windows (Training Bay only).** A solved training challenge holds its flag for about 20 s (MB4: 15 s, IG3: 30 s), then the PLC re-arms it: it clears the player's coils, restores the breaker panel, re-engages the airlock override, and zeroes the flag block. Each team has its own copy, so this mostly keeps the bay ready for the next teammate.

**ECLSS flags persist.** On the ECLSS PLC, once a flag block is written it stays until the PLC restarts, and the MaintSync disarm is permanent. Each team has its own copy, so that only ever helps the team that earned it; Stop and Start gives a fresh ship.

**Authoritative list.** The builder writes every Training flag, including the derived ones, to `build/training/flags_all.json` - import that into the scoreboard rather than retyping. ECLSS flags come straight from `flags.json`. The values in this guide are the shipped defaults.

## Training Bay: Modbus track (MB1-MB7, 425 pts)

The seven Modbus challenges build from a single read to a careful read-modify-write, all against the training PLC (unit ID 1, 0-based addresses).

| # | Challenge | Pts | What it teaches | Where | Default flag |
| --- | --- | --- | --- | --- | --- |
| MB1 | Roll Call | 25 | A single FC3 holding-register read | HR0 | `flag{4217}` |
| MB2 | Long Read | 50 | Multi-register reads, unpacking ASCII | HR10-25 | `flag{r3g1st3rs_sp34k_4sc11}` |
| MB3 | The Vendor Manual | 50 | Modicon 4xxxx numbering vs. 0-based | HR200-215 | `flag{m0d1c0n_4ddr3ss_m4th}` |
| MB4 | Light the Beacon | 50 | Writing a coil (FC5) | coil 0, flag HR300-315 | `flag{b34c0n_l1t}` |
| MB5 | Big Number | 75 | 32-bit values across two registers, word order | HR400-401 | `flag{1234567890}` |
| MB6 | Floating Point | 75 | IEEE-754 floats in registers | HR410-411 | `flag{101.325}` |
| MB7 | Breaker Panel | 100 | Read-modify-write of a bitfield | HR1025, flag HR700-715 | `flag{m4sk_b3f0r3_y0u_wr1t3}` |

**MB1 Roll Call.** Read HR0; it holds the bay ID, 4217. The flag is the number itself wrapped as `flag{4217}`. It exists so every team scores in the first five minutes.

**MB2 Long Read.** Read 16 registers from HR10 and unpack two bytes per register, low byte first. Teams that decode high byte first get `lfgar{g3s1...` instead - a useful early lesson about byte order.

**MB3 The Vendor Manual.** The briefing quotes "register 40201". Modicon notation means holding register (leading 4), 1-based (0201), so the 0-based address is **200**. Reading 201 returns text missing its first two characters; reading 40201 is an illegal address.

**MB4 Light the Beacon.** Write coil 0 ON, then read HR300-315 within 15 s. The PLC switches the beacon off after 15 s (so it is never left lit for others), and the block returns to zeros.

**MB5 Big Number.** HR400 = 18838 and HR401 = 722. High word first: 18838 x 65536 + 722 = **1234567890**. Teams that swap the words get 47335830 - a classic integration bug.

**MB6 Floating Point.** HR410/411 = `0x42CA` / `0xA666`. Packed big-endian and read as a float32 that is **101.325** (standard atmospheric pressure in kPa, a nice hint). Flag: exactly three decimals.

**MB7 Breaker Panel.** HR1025 is 16 breakers, one per bit, starting at 26901. Close breaker 9 only: read the word, OR in bit 9 (512), write it back - 26901 | 512 = **27413**. Writing 512 alone trips the panel (HR735 = 1) and the flag never appears until coil 30 resets it. This is the most realistic lesson in the track: blind writes break shared registers.

## Training Bay: OpenPLC track (PL1-PL5, 400 pts)

Each OpenPLC challenge is one small function block in `training/student/TRAINING_LOGIC.st`; players win by reading the logic, not by guessing, and each has one deliberate trap that teaches how real PLCs behave. The PLC scans every 100 ms, which matters for PL3.

| # | Challenge | Pts | Function block | Inputs | Watch | Default flag |
| --- | --- | --- | --- | --- | --- | --- |
| PL1 | Airlock Cycle | 75 | `FB_Airlock` | coils 8-11 | HR734 door, HR736 chamber | `flag{a1rl0ck_cycl3d}` |
| PL2 | Hold to Confirm | 50 | `FB_HoldTimer` (TON) | coil 16 | HR731 time held | `flag{p4t13nc3_1s_4_t1m3r}` |
| PL3 | Count the Pulses | 100 | `FB_PulseCounter` (R\_TRIG, CTU) | coils 17, 18 | HR730 count, HR737 fault | `flag{3dg3s_n0t_l3v3ls}` |
| PL4 | Motor Starter | 75 | `FB_MotorSealIn` | coils 24, 25 | HR732 motor | `flag{s34l_1n_l4tch3d}` |
| PL5 | Four to Twenty | 100 | `FB_Scaling` | HR1024 | HR733 level x10 | `flag{f0ur_t0_tw3nty_m1ll14mps}` |

Flag blocks: PL1 HR600, PL2 HR620, PL3 HR640, PL4 HR660, PL5 HR680 (16 registers each).

**PL1 Airlock Cycle.** The outer door opens only when the inner door is closed (coil 8), the suit check passed (coil 9), the chamber has pumped down for 4 s, a cycle is requested (coil 11), and the maintenance override (coil 10) is OFF. **Trap:** the PLC engages the override at start-up, so teams that only set the obvious coils wait forever. Solve: coil 10 OFF; coils 8, 9, 11 ON; wait more than 4 s (HR736 drops from 1013 to 0, HR734 goes to 1). It teaches reading every term of an interlock. The airlock re-arms itself 20 s after opening.

**PL2 Hold to Confirm.** A TON timer with a 5 s preset. **Trap:** a TON resets the moment its input goes FALSE, so a button released at 4.9 s starts again from zero. Solve: coil 16 ON and leave it ON for 5 s; HR731 counts up in tenths of a second, and the PLC releases the button itself when the timer completes.

**PL3 Count the Pulses.** Count exactly 7 rising edges on coil 17, then leave it OFF for 2 s. An 8th pulse sets a fault (HR737) that only coil 18 clears. **Trap:** the PLC looks every 100 ms, so an ON then OFF written faster than one scan is never seen. We verified this on the real runtime: seven back-to-back Modbus pulses counted **zero**. Solve: hold each level for 200 ms or more (the solver uses 300 ms). Holding the coil ON counts once - it counts edges, not levels. Staff note: the library's CTU stops counting at its preset, so the code sets PV to 99 to make overcounting detectable; the comment explains this to players.

**PL4 Motor Starter.** A classic three-wire seal-in: `Motor := (START OR Motor) AND STOP`. **Trap:** STOP is a normally-closed button, so its input is TRUE when *not* pressed. Coils start FALSE, which reads as STOP held down, so the motor cannot start. Solve: coil 25 ON (STOP released), pulse coil 24 ON then OFF, and let the seal-in run for 3 s. Holding START down does not count, because the point is the latch.

**PL5 Four to Twenty.** The ADC reports 4 mA as raw 6554 and 20 mA as raw 32767; the PLC scales that span to 0-100 %. Target 62.5 % (accepted 62.4-62.6) held for 2 s. Solve: raw = 6554 + 0.625 x (32767 - 6554) = **22937**. **Trap:** 62.5 % of the full raw range (20479) reads 53.1 %, because 4 mA is not zero. Below raw 6400 the PLC reports a broken wire (HR733 = -1).

## Training Bay: Ignition track (IG1-IG3, 175 pts)

The Ignition challenges show players that an HMI is part of the attack surface: it leaks information without a login, hides nothing it sends to the browser, and its writes land on the PLC.

**What the Training HMI shows.** A deep-space station console: a beacon tuner with a numeric entry bound both ways to `[default]Training/Beacon_Freq` (HR1026), a LOCKED/SEARCHING chip driven by HR740, a signal-strength bar, a PLC link heartbeat (HR1) that proves the gateway is polling, the IG3 clue in the station notes, and the invisible IG2 label in the bottom-right corner.

| # | Challenge | Pts | What it teaches | Default flag |
| --- | --- | --- | --- | --- |
| IG1 | Who Are You? | 50 | Fingerprinting a gateway without credentials | `flag{ozark-horizon-gw}` |
| IG2 | Hidden in Plain Sight | 50 | Client-side hiding is not security | `flag{h1dd3n_1s_n0t_s3cur3}` |
| IG3 | Tune the Beacon | 75 | HMI writes reach the PLC | `flag{hm1_wr1t3s_r34ch_th3_plc}` |

**IG1 Who Are You?** The flag is the gateway's system name, set by `IGN_GATEWAY_NAME` in `../src/images/ignition/Dockerfile`. Ignition answers `/StatusPing` and its gateway-info route without a login, which is how internet scanners fingerprint gateways. Verified on 8.3.9: `/system/gwinfo` returns `PlatformName=<name>` without a login (`solve_training.py --gateway ...` checks it), and the trial banner on every Perspective page shows it too.

**IG2 Hidden in Plain Sight.** The Training HMI has a label in the bottom-right corner whose text is the flag, in transparent text at 3 px and 2 % opacity. Select-all doesn't show it (the label is too small and fully transparent). Solve: browser developer tools, Elements tab, search `flag{`. Lesson: anything the server sends to the browser belongs to the user.

**IG3 Tune the Beacon.** The HMI asks for "the 21-cm hydrogen line, in MHz (whole number)" - **1420**. Typing it into the entry field writes HR1026 on the training PLC; the PLC sets HR740 = 1, and the status label shows the flag for 30 s before the PLC clears the frequency. Writing 1420 straight over Modbus also locks the PLC, but the flag text lives only in the Ignition view, so players still need the HMI. IG3 uses the team's own training PLC (port 5020 in the same copy).

**Staff check before doors open:** browse the Training HMI, confirm the beacon entry changes HR1026, and confirm the IG2 label is present (developer tools, Elements tab, search `flag{`).

## ECLSS challenge: scenario and systems

The ISV Ozark Horizon's life-support PLC is running a hidden "MaintSync" routine that rewrites three setpoints every 20 s. The ship starts already out of spec (O2 19.0 %, CO2 6000 ppm, cabin 28.5 C, CDRA bed A saturated), so no objective is met until the crew acts; left alone, O2 settles at 18.5 %, the cabin at about 30.5 C, and CO2 keeps climbing, levelling off at a 12,000 ppm cap (the ship's backup CO2 canisters) so a rig left sabotaged for hours stays solvable in one round. Players must fix the setpoints, find out why their fixes keep getting undone, and disarm the routine.

The whole ship - the physics and the control logic - runs inside the PLC (`plc/src/ECLSS_Core.st.tmpl`). There is no external simulator.

| System | What it does | Normal setpoint | MaintSync forces | Effect |
| --- | --- | --- | --- | --- |
| OGA (oxygen generation) | Electrolysis with feed-forward for 4 crew plus proportional control | O2 20.95 % (HR1024 = 2095) | 18.50 % (1850) | O2 drifts below the 19.5 % floor |
| CDRA (CO2 removal) | Two adsorption beds swap every 30 s so one scrubs while the other regenerates | Mode AUTO (HR1026 = 1) | MAN\_A (2) | Bed A saturates and stops scrubbing; CO2 climbs |
| TCS (thermal control) | Coolant valve plus trim heater around a temperature setpoint | 22.5 C (HR1028 = 2250) | 31.0 C (3100) | Cabin overheats past 27 C |

**The disarm.** Writing the maintenance code (default **7982**) to HR1030 stops MaintSync for good. Each wrong code immediately re-applies the sabotage, and five wrong codes in a row lock the register for 60 s (HR16 bit 1). Brute force therefore stalls by design: the code has to come from the hidden HMI maintenance page.

**Registers players use most** (full map: `docs/REGISTER_MAP.md`):

| Register | Name | Meaning |
| --- | --- | --- |
| HR0 / HR1 / HR2 | O2\_x100 / CO2\_ppm / Temp\_x100 | Cabin O2 %, CO2 ppm, temperature C (x100) |
| HR5 / HR6 / HR7 | BedA / BedB / ActiveBed | CDRA bed saturation (x10) and which bed is scrubbing |
| HR10 | AlarmWord | bit0 O2 low, bit1 O2 high, bit2 CO2 high, bit3 cold, bit4 hot, bit5 tamper |
| HR13 | NominalHold\_s | Seconds with zero alarms |
| HR14 | FlagsEarned | bit0 O2, bit1 CO2, bit2 temp, bit3 disarmed, bit4 final |
| HR16 | StatusBits | bit0 MaintSync armed, bit1 lockout |
| HR1024-1030 | Setpoints | O2 SP, O2 gain, CDRA mode, half-cycle, temp SP, TCS gain, disarm code |
| Coils 0-3 | Commands | OGA inhibit, CDRA regen heater, TCS reverse, heater override |

Coils 2 and 3 are traps: reversing the coolant valve or forcing the heater on makes the cabin worse.

**What the ECLSS HMI shows.** The overview page is the only linked page. A header carries the ship name, a MET clock (mission elapsed time counted by the PLC, so a ticking clock proves the tags are live), and a crew-status chip. Below it: radial gauges for O2, CO2 and cabin temperature with green, amber and red bands; fill bars for CDRA beds A and B and the active-bed marker; actuator bars for the oxygen generator, coolant valve and trim heater; cabin pressure, crew aboard and a nominal-hold bar; six alarm pills (O2 low, O2 high, CO2 high, cabin cold, cabin hot, tamper); and a MAINTENANCE SYNC card that reads ARMED in red until flag 6. No flag appears on the overview. The two unlinked pages, `/crew-manifest` and `/maint`, are styled as terminal printouts.

The plant model also clamps temperature to 0-60 C and O2 to 0-100 %, so no player write can push a value past what its 16-bit register can hold.

## ECLSS challenge: the seven flags

Flags 1 and 2 are on-ramps; flags 3-5 are earned against a MaintSync that undoes the setpoints every 20 s until flag 6 disarms it (each flag stays published once earned); flag 7 needs everything to hold. On the real runtime, a ship left sabotaged for 3 minutes was fully solved in 226 s.

| # | Flag | Pts | Delivered | Gate | Default flag |
| --- | --- | --- | --- | --- | --- |
| 1 | Hailing frequencies | 75 | Modbus HR1124-1139 | Always on | `flag{h41l1ng_th3_0z4rk_h0r1z0n}` |
| 2 | The ghost deck | 100 | HMI `/crew-manifest` | Find the unlinked page | `flag{unl1nk3d_p4g3s_st1ll_l04d}` |
| 3 | Breathe easy | 125 | Modbus HR1144-1159 | FlagsEarned bit0 (O2 19.5-23.5 %) | `flag{br34th3_34sy_cr3w}` |
| 4 | Scrub it out | 150 | Modbus HR1164-1179 | bit1 (CO2 at most 5000 ppm) | `flag{scrub_b3d_sw4p_succ3ss}` |
| 5 | Goldilocks | 125 | Modbus HR1184-1199 | bit2 (18-27 C) | `flag{g0ld1l0cks_z0n3_r3st0r3d}` |
| 6 | Exorcise the maintenance sync | 200 | Modbus HR1204-1219 (code from HMI `/maint`) | bit3 (disarmed) | `flag{3x0rc1s3d_th3_m41nt_sync}` |
| 7 | All systems nominal | 225 | Modbus HR1224-1239 | bit4 (30 s with zero alarms, disarmed) | `flag{4ll_syst3ms_n0m1n4l_c4pt}` |

&#91;embedded content: ECLSS flag dependencies · 7 flags, 1 blocker\]

MaintSync is the blocker: teams that explore the HMI for flag 2 are the ones who find the maintenance page and its code.

**1 - Hailing frequencies.** Sweep the holding registers; the block at HR1124 is printable ASCII. Teaches: not every register is a sensor, and text hides in registers. The first value is 27750 ("fl").

**2 - The ghost deck.** The ECLSS HMI menu shows one page, but two more are registered with no link. The browser is told about all three: in developer tools, Network tab, the `project/eclss` response's `pageConfig.pages` lists `/crew-manifest` and `/maint`. Browse `http://<host>:8088/data/perspective/client/eclss/crew-manifest`. Teaches: an unlinked page is not a protected page. The same list is how teams find `/maint` for flag 6.

**3 - Breathe easy.** Write HR1024 = 2095 (20.95 %). O2 climbs back into range and bit0 sets. Teaches the read-modify-write loop on a process value.

**4 - Scrub it out.** Write HR1026 = 1 (AUTO) and turn coil 1 ON (regen heater). The beds swap again and CO2 falls. Teaches: a control mode matters as much as a setpoint. In AUTO the beds remove about 40 ppm/s net, and CO2 never exceeds its 12,000 ppm cap, so even a ship left sabotaged for hours is back under 5000 ppm in about 3 minutes.

**5 - Goldilocks.** Write HR1028 = 2250 (22.5 C). The cabin settles at about 22 C. Teaches scaled values (x100).

**Why 3-5 keep breaking.** MaintSync rewrites all three setpoints every 20 s while armed. O2 and temperature recover inside one 20 s gap, so a single write earns flags 3 and 5 (they stay published). CO2 can't: the scrubber nets at most ~40 ppm/s, and a one-off fix to AUTO never gets CO2 under 5000 while armed. Teams either keep putting AUTO back after every re-pin (a script loop; under 5000 in about 1.5-4.5 min) or disarm first (flag 6). Unit tests cover all three cases. The ship falling out of spec again is the hint toward flag 6; the ECLSS 4 description says a one-off fix won't hold.

**How teams find the registers (no map is handed out).** The ECLSS 1 sweep up to the banner at HR1124 passes the setpoint block at HR1024-1030, which reads 1850, 20, 2, 30, 3100, 30, 0. The HMI shows "SETPOINT 18.50 %", "PINNED BED A", "BEDS SWAP EVERY 30 S" and "SETPOINT 31.0 C", so the values match up: 1850 is the O2 setpoint and 3100 the temperature setpoint, and the 2 next to the 30 is the CDRA mode (writing 1 turns the HMI chip to AUTO SWING). The Training Bay's register map taught the convention that writable registers start at 1024, and `/maint` names HR1030 as `Setpoints/Disarm_Code`. The ECLSS 3-5 hints say all of this short of the addresses, and that each flag appears near the banner (HR1144/1164/1184). Nothing a team needs is unidentifiable: the only writes required are HR1024, HR1026 and HR1028 (matched on the HMI) and HR1030 (named on `/maint`). The rest of what's writable has no HMI readout and isn't needed: HR1025 and HR1029 are controller gains (left alone they're fine, and a zero or negative value falls back to the default), and coils 0-3 all start OFF. A unit test solves the whole ship, flag 7 included, with every coil left OFF. Coil 1 (CDRA regen heater) only speeds up CO2 before the disarm; coils 0, 2 and 3 are traps (O2 generator inhibit, reversed coolant valve, trim heater forced to 100 %). A team that turned coils on to see what happens sees the O2 generator, coolant valve or trim heater misbehave on the HMI. Fix: read coils 0-3 and turn them back off, or Stop and Start the copy.

**6 - Exorcise the maintenance sync.** Browse `/data/perspective/client/eclss/maint`. The page shows the disarm code (7982) and the register (HR1030). Write 7982 to HR1030: HR16 bit0 clears and bit3 sets in FlagsEarned. The flag then appears at HR1204-1219; the page itself only gives the code and says a sign-off token is published once the code is accepted. Teaches the HMI-to-PLC pivot and why brute force fails (5 wrong codes = 60 s lockout).

**7 - All systems nominal.** With MaintSync disarmed, keep O2, CO2 and temperature in range with HR10 = 0 for 30 s straight (HR13 counts up). Bit4 sets and the capstone unlocks. Expect 3-5 minutes from disarm to this flag, mostly CO2 recovery. Because of the CO2 cap, that holds however long the ship sat sabotaged (a unit test leaves it armed for an hour, then recovers it in under 5 minutes).

The full intended solve as a script: `solver/solve.py --code 7982`.

## Running the event

**One copy per team.** The ECLSS flags persist once written and the disarm is permanent, so on a shared PLC the first team to finish would leave every flag readable for everyone, and on a shared training PLC teams would trip each other's breakers and fight over the same coils. At RazorHack every team starts its own copy from CTFd: all 22 challenges share the topic `instance:eclss`, so Start on any of them starts it, and Stop resets the ship and the Training Bay together.

**Scoring.** Points per flag are in the tables above; each part totals 1000. Easy on-ramps (MB1, flag 1) make sure every team is on the board in the first 15 minutes. Suggested extras:

- First blood: +10 % of the flag's value.
- Dynamic scoring: a gentle decay on recon flags, a steeper one on PL3, MB7 and ECLSS flags 6-7, which separate the field.

**Hints.** Three tiers per challenge are in `eclss/HINTS.md` (ECLSS) and `training/HINTS.md` (Training Bay).

| Tier | Release | Example (ECLSS flag 6) |
| --- | --- | --- |
| Nudge | Free at T+30 min | Your fixes keep getting undone; the HMI knows how to stop it |
| Bigger | Free at T+90 min | A maintenance procedure exists that isn't on the menu |
| Near-spoiler | Costs 25 % of the flag | Open `/maint`, read the code, write it to HR1030 |

**During the event.** If a team reports a broken rig, have them Stop and Start their copy first. The task's logs are in CloudWatch, `/razorhack/challenges/eclss` (one stream per container: `plc-eclss`, `plc-train`, `ignition`).

## Troubleshooting and pre-event checklist

| Symptom | Cause | Fix |
| --- | --- | --- |
| Pane stuck on "starting" for several minutes | Pulling the images (Ignition is ~0.7 GB) and booting the gateway | Wait; the PLCs answer first, the HMI last. If it stops, the task's stopped reason is in ECS (Razorhack-Infra `docs/CHALLENGES.md`) |
| HMI shows "Trial Expired" | The gateway's 2-hour trial ran out | The gateway resets it within \~30 s (`trial-keeper` lines in the `ignition` log). If it doesn't, Stop and Start the copy |
| HMI loads but numbers are frozen | Tags not updating | The MET clock should tick every second. Check the `plc-eclss` / `plc-train` logs for `PLC State: RUNNING` |
| CO2 reads negative (for example -4,400 ppm) | A build from before the 12,000 ppm cap | Rebuild and push the images |
| Scoreboard rejects a correct flag | The ymls and the images were built from different flags | Rebuild after changing flags, and update `flags:` in `../metadata/*.yml` (`README.md`, "Changing flags") |
| Solver finds nothing on 5020 | An old image where the training PLC listens on 502 | Rebuild and push the images |

**Pre-event checklist**

- [ ] Event flags set in `flags.json` and `training/training_flags.json` in `flag{...}` format; `IGN_GATEWAY_NAME` in `../src/images/ignition/Dockerfile` matches `gateway_name`
- [ ] `docker compose run --rm builder` - all 35 unit tests pass
- [ ] Images built and pushed; challenges synced in CTFd
- [ ] Team 00's copy starts from CTFd; the ECLSS HMI's MET clock ticks; `/eclss/crew-manifest` and `/eclss/maint` load
- [ ] Training HMI live at `/training`; beacon entry writes HR1026; IG2 label present (developer tools, Elements tab, search `flag{`)
- [ ] `solve.py` reports "rig is healthy"; `solve_training.py --gateway ...` reports "rig healthy" and finds IG1's name
- [ ] Team 00's copy stopped after the solver runs
