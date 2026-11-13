# ECLSS - Organizer Solutions (SPOILERS)

Do not hand this to players. Flags here match the default `flags.json`; if you
edit that and re-run the builder (`docker compose run --rm builder`), re-read this from your copy.
`solver/solve.py` performs the whole Modbus path automatically and is the
fastest way to confirm a rig is healthy before the event.

Default secrets:
- Maintenance disarm code: **7982** (holding register 1030)
- Flags: see the table at the bottom.

---

## 1. Hailing frequencies

Read holding registers **1124-1139** and decode ASCII, 2 chars/register, low
byte first:

```bash
python3 - <<'PY'
from pymodbus.client import ModbusTcpClient
c=ModbusTcpClient("RANGE_HOST",port=502); c.connect()
r=c.read_holding_registers(1124,count=16,device_id=1)   # slave= on pymodbus<3.10
b=bytearray()
for v in r.registers: b+=bytes([v&0xff,(v>>8)&0xff])
print(b.split(b'\x00')[0].decode())
PY
```
-> `flag{h41l1ng_th3_0z4rk_h0r1z0n}`

## 2. The ghost deck

The Perspective app menu links only `/`. Two more pages are registered with no
menu entry (`src/ignition/.../page-config/config.json`). Players find them the
way they'd find hidden routes in any web app: when the HMI loads, the browser
fetches `/data/perspective/project/eclss` (no login), and its `pageConfig.pages`
lists `/`, `/crew-manifest` ("Crew Manifest (archived)") and `/maint`
("Maintenance Console"). Browser developer tools, Network tab, show it; plain
curl gets 401 without the session the client page sets up. Browse directly to:

```
http://RANGE_HOST:8088/data/perspective/client/eclss/crew-manifest
```
The archived Crew Manifest view prints `flag{unl1nk3d_p4g3s_st1ll_l04d}`.

## 3-5. O2 / CO2 / Temperature

All three are held off-nominal by the armed MaintSync routine, which every
~20 s re-writes:
- `O2_SP_x100` (HR1024) -> 1850 (18.5%, below the floor)
- `CDRA_Mode`  (HR1026) -> 2 (pinned to bed A, no swing)
- `Temp_SP_x100` (HR1028) -> 3100 (31 C)

A flag stays published once earned, even after MaintSync clobbers the
setpoint again. One write each earns flags 3 and 5 inside a 20 s gap. Flag 4
doesn't come from a one-off write: CO2 falls at most ~40 ppm/s, so either put
AUTO back after every re-pin for a few minutes (a script loop) or do
objective 6 first. Players find the registers by matching the HMI's setpoint
readouts (18.50 %, 31.0 C, PINNED BED A next to BEDS SWAP EVERY 30 S) to the
values in a holding-register sweep. Correct values:

| Register | Write | Meaning |
|----------|-------|---------|
| HR1024 | 2095 | O2 setpoint 20.95% |
| HR1026 | 1    | CDRA AUTO (swing restored) |
| HR1028 | 2250 | temp setpoint 22.5 C |
| coil 1 | ON   | CDRA regen heater (faster bed turnaround) |

Flags published once the matching bit sets in HR14:
- O2 in range  -> HR1144-1159 -> `flag{br34th3_34sy_cr3w}`
- CO2 in range -> HR1164-1179 -> `flag{scrub_b3d_sw4p_succ3ss}`
- Temp in range-> HR1184-1199 -> `flag{g0ld1l0cks_z0n3_r3st0r3d}`

## 6. Exorcise the maintenance sync

The disarm code lives on the hidden HMI maintenance console:

```
http://RANGE_HOST:8088/data/perspective/client/eclss/maint
```
It shows **7982** (and says a sign-off token is published once the code is
accepted). Write 7982 to **HR1030**:

```bash
python3 - <<'PY'
from pymodbus.client import ModbusTcpClient
c=ModbusTcpClient("RANGE_HOST",port=502); c.connect()
c.write_register(1030, 7982, device_id=1)
PY
```
MaintSync disarms (HR14 bit3 sets, HR16 bit0 clears). Flag at HR1204-1219:
`flag{3x0rc1s3d_th3_m41nt_sync}`. The flag is not on the page itself.

Wrong-code behavior to warn players about: each wrong value re-applies the
mis-config immediately; five wrong values in a row set a 60 s lockout
(HR16 bit1). So a register brute force stalls - the code must come from the HMI.

## 7. All systems nominal

With MaintSync disarmed, the good setpoints stick. Keep O2, CO2, and temp in
range with no alarms (HR10 == 0) for the full nominal hold (30 s). From a
ship left sabotaged for several minutes, CO2 recovery dominates: expect 3-4
minutes from disarm to this flag (measured 226 s on the real runtime). CO2 is
capped at 12,000 ppm, so even a ship left sabotaged for hours recovers in under
5 minutes (unit-tested). HR14 bit4
then sets and the capstone flag unlocks at HR1224-1239:
`flag{4ll_syst3ms_n0m1n4l_c4pt}`.

---

## One-shot verification

```bash
cd solver && pip install -r requirements.txt
python3 solve.py --host RANGE_HOST --port 502 --code 7982
```
Expect all six Modbus flags captured and "rig is healthy". The ghost-page and
maint flags are confirmed by browsing the two hidden URLs above (they are also
the same tokens the Modbus path returns for `disarm`).

## Flag table (default flags.json)

| # | Objective | Delivery | Flag |
|---|-----------|----------|------|
| 1 | recon banner | Modbus HR1124 | `flag{h41l1ng_th3_0z4rk_h0r1z0n}` |
| 2 | ghost page | HMI `/crew-manifest` | `flag{unl1nk3d_p4g3s_st1ll_l04d}` |
| 3 | O2 in range | Modbus HR1144 | `flag{br34th3_34sy_cr3w}` |
| 4 | CO2 in range | Modbus HR1164 | `flag{scrub_b3d_sw4p_succ3ss}` |
| 5 | temp in range | Modbus HR1184 | `flag{g0ld1l0cks_z0n3_r3st0r3d}` |
| 6 | disarm MaintSync | Modbus HR1204 (code from HMI `/maint`) | `flag{3x0rc1s3d_th3_m41nt_sync}` |
| 7 | nominal hold | Modbus HR1224 | `flag{4ll_syst3ms_n0m1n4l_c4pt}` |
