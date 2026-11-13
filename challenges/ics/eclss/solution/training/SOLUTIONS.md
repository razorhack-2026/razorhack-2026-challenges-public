# Training Bay - Staff Solutions & Scoring (SPOILERS)

Values below are for the default `training/training_flags.json`. The
authoritative list for **your** build is `build/training/flags_all.json`
(written by the builder) - import that into your scoreboard, not this page.

## Scoring (1000 points total, same scale as the ECLSS challenge)

| # | Challenge | Skill | Pts | Default flag |
|---|-----------|-------|-----|--------------|
| MB1 | Roll Call | FC3 single read | 25 | `flag{4217}` |
| MB2 | Long Read | multi-register read, ASCII unpack | 50 | `flag{r3g1st3rs_sp34k_4sc11}` |
| MB3 | The Vendor Manual | Modicon 4xxxx -> 0-based | 50 | `flag{m0d1c0n_4ddr3ss_m4th}` |
| MB4 | Light the Beacon | FC5 write coil | 50 | `flag{b34c0n_l1t}` |
| MB5 | Big Number | 32-bit word order | 75 | `flag{1234567890}` |
| MB6 | Floating Point | IEEE-754 from registers | 75 | `flag{101.325}` |
| MB7 | Breaker Panel | read-modify-write bitmask | 100 | `flag{m4sk_b3f0r3_y0u_wr1t3}` |
| PL1 | Airlock Cycle | reading interlock logic | 75 | `flag{a1rl0ck_cycl3d}` |
| PL2 | Hold to Confirm | TON timers | 50 | `flag{p4t13nc3_1s_4_t1m3r}` |
| PL3 | Count the Pulses | edges vs levels, scan time | 100 | `flag{3dg3s_n0t_l3v3ls}` |
| PL4 | Motor Starter | seal-in, NC contacts | 75 | `flag{s34l_1n_l4tch3d}` |
| PL5 | Four to Twenty | 4-20 mA scaling | 100 | `flag{f0ur_t0_tw3nty_m1ll14mps}` |
| IG1 | Who Are You? | gateway fingerprinting | 50 | `flag{ozark-horizon-gw}` |
| IG2 | Hidden in Plain Sight | client-side "security" | 50 | `flag{h1dd3n_1s_n0t_s3cur3}` |
| IG3 | Tune the Beacon | HMI writes reach the PLC | 75 | `flag{hm1_wr1t3s_r34ch_th3_plc}` |

## Walkthrough

**MB1** Read HR0 -> 4217.
**MB2** Read HR10-25, unpack low byte first.
**MB3** 40201 is Modicon 1-based -> HR200. Reading 201 or 40201 gives garbage.
**MB4** Coil 0 ON; HR300-315 hold the flag until the PLC turns the beacon off at 15 s.
**MB5** HR400 = 18838, HR401 = 722 -> 18838 x 65536 + 722 = 1234567890.
**MB6** HR410/411 = 0x42CA / 0xA666 -> 101.325 as float32.
**MB7** HR1025 starts at 26901. Write 26901 | 512 = 27413. Writing 512 alone trips the panel (HR735 = 1); coil 30 resets it to 26901.
**PL1** At start the PLC engages Override (coil 10). Coil 10 OFF, coils 8, 9, 11 ON. After the 4 s pump-down (HR736 -> 0) the door opens.
**PL2** Coil 16 ON continuously for 5 s. The PLC releases the button itself when the timer completes.
**PL3** Seven ON/OFF pulses, each level held >= 2 scans (>= 200 ms), then OFF for 2 s. Toggling without a delay registers **zero** counts - verified on the real runtime; that is the lesson. An 8th pulse faults (HR737); coil 18 resets.
**PL4** Coil 25 ON (STOP is normally-closed: TRUE = released), coil 24 ON then OFF; the seal-in keeps the motor running; 3 s later it unlocks. Holding START does not count.
**PL5** Raw 22937 -> 62.5 % (HR733 = 625). The naive 0.625 x 32767 = 20479 reads 53.1 %.
**IG1** The gateway system name (`IGN_GATEWAY_NAME` in `src/images/ignition/Dockerfile`, passed as `-n`). On 8.3.9, `/system/gwinfo` returns `PlatformName=<name>` without a login (`solve_training.py --gateway http://<host>:8088` checks it), and the trial banner on every Perspective page shows it too.
**IG2** Training HMI bottom-right: a label in transparent text at 3 px and 2 % opacity. Select-all doesn't show it; developer tools, Elements tab, search `flag{`, does.
**IG3** Clue = 21-cm hydrogen line = 1420 MHz. Type 1420 + Enter; the HMI writes HR1026 on the training PLC, the PLC sets HR740 = 1, and the status label shows the flag for 30 s. Writing 1420 straight over Modbus also locks the PLC side - but the flag text exists only in the Ignition view, so players still need the HMI.

## One copy per team

Every success holds ~20 s and the PLC then re-arms the challenge (clears the
coils, restores the panel, re-engages the override). Each team has its own
copy of the rig (`instance:eclss`, `../README.md`), so teams never trip each
other's breakers or fight over the same coils, and IG3 runs against the team's
own training PLC.

## Pre-event checklist

1. Edit `training/training_flags.json` (and `IGN_GATEWAY_NAME` in
   `src/images/ignition/Dockerfile` to match `gateway_name`), then
   `docker compose run --rm builder`. The builder also runs the 20 PLC unit
   tests - they must all pass.
2. Build and push the images, and start team 00's copy (`../README.md`).
3. `python3 solution/training/solve_training.py --host <host> --port 5020 --gateway http://<host>:8088`
   -> "rig healthy". Then wait ~30 s so every success window closes.
4. Browse the Training HMI: confirm the beacon entry writes (HR1026 changes)
   and the hidden IG2 label is present.
