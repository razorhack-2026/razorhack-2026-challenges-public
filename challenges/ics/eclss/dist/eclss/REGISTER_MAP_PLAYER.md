# Modbus Register Map - ISV Ozark Horizon

Flight-deck reference for the life-support controller. Modbus TCP,
unit id 1, port 502. All values are 16-bit signed INT; scaled values
are stored x10 or x100 (divide to read).

## Telemetry - Holding Registers (function code 3), read

| HR | Name | Meaning |
|----|------|---------|
| 0 | O2_x100 | cabin O2 %, x100 |
| 1 | CO2_ppm | cabin CO2, ppm |
| 2 | Temp_x100 | cabin temp degC, x100 |
| 3 | Press_x10 | cabin pressure kPa, x10 |
| 4 | OGA_x10 | O2 generator output %, x10 |
| 5 | BedA_x10 | CDRA bed A saturation %, x10 |
| 6 | BedB_x10 | CDRA bed B saturation %, x10 |
| 7 | ActiveBed | 1=A adsorbing, 2=B adsorbing |
| 8 | Valve_x10 | coolant valve %, x10 |
| 9 | Heater_x10 | trim heater %, x10 |
| 10 | AlarmWord | bit0 O2lo bit1 O2hi bit2 CO2hi bit3 cold bit4 hot |
| 11 | CrewStatus | 0 OK / 1 WARN / 2 CRIT |
| 12 | MET_s | mission elapsed time, s |
| 15 | CrewCount | souls aboard |

## Setpoints / Commands - Holding Registers (FC 3 read / FC 6,16 write)

| HR | Name | Meaning |
|----|------|---------|
| 1024 | O2_SP_x100 | O2 setpoint %, x100 (nominal 2095) |
| 1025 | O2_Kp_x10 | OGA gain, x10 |
| 1026 | CDRA_Mode | 0 OFF / 1 AUTO / 2 MAN_A / 3 MAN_B |
| 1027 | CDRA_HalfCycle_s | bed swing half-cycle, s |
| 1028 | Temp_SP_x100 | temp setpoint degC, x100 (nominal 2250) |
| 1029 | TCS_Kp_x10 | TCS gain, x10 |

## Commands - Coils (FC 1 read / FC 5 write)

| Coil | Name | Meaning |
|------|------|---------|
| 0 | OGA_Inhibit | stop oxygen generation |
| 1 | CDRA_Heater_En | enable CDRA regen heater |
| 2 | TCS_Reverse | reverse coolant valve action |
| 3 | Heater_Override | force trim heater to 100% |
