# Training Bay - Register Map

Modbus TCP, unit id 1. Holding registers are 0-based, 16-bit signed.
Text blocks: ASCII, 2 chars per register, low byte first.

## Coils (FC1 read / FC5 write)

| Coil | Name | Purpose |
|---|---|---|
| 0 | Beacon_On | MB4 beacon command |
| 8 | Inner_Closed | PL1 inner door closed |
| 9 | Suit_Ok | PL1 suit check passed |
| 10 | Override | PL1 maintenance override |
| 11 | Cycle_Req | PL1 request outer door |
| 16 | Hold_Btn | PL2 confirm button |
| 17 | Pulse_In | PL3 pulse input |
| 18 | Count_Reset | PL3 counter reset |
| 24 | Start_PB | PL4 START (normally open) |
| 25 | Stop_PB_NC | PL4 STOP (normally CLOSED) |
| 30 | Breaker_Reset | MB7 panel reset |

## Player-writable holding registers (FC3 / FC6, FC16)

| HR | Name | Purpose |
|---|---|---|
| 1024 | Analog_Raw | PL5 raw 4-20 mA ADC value |
| 1025 | Breaker_Word | MB7 breaker bitfield |
| 1026 | Beacon_Freq | IG3 beacon frequency (set it from the HMI) |

## Read-only holding registers (FC3)

| HR | What | Notes |
|---|---|---|
| 0 | Bay_Id | MB1 |
| 1 | Heartbeat | increments every scan (100 ms) |
| 10..25 | text block | MB2 |
| 200..215 | text block | MB3 (see briefing) |
| 300..315 | text block | MB4, while the beacon is lit |
| 400..401 | 32-bit value | MB5 |
| 410..411 | 32-bit value | MB6 |
| 600..615 | text block | PL1 |
| 620..635 | text block | PL2 |
| 640..655 | text block | PL3 |
| 660..675 | text block | PL4 |
| 680..695 | text block | PL5 |
| 700..715 | text block | MB7 |
| 730 | Diag_Count | PL3 counter value |
| 731 | Diag_Hold | PL2 time held, 0.1 s |
| 732 | Diag_Motor | PL4 motor running (1/0) |
| 733 | Diag_Eng | PL5 scaled level, % x10 (-1 = wire break) |
| 734 | Diag_Door | PL1 outer door open (1/0) |
| 735 | Diag_Trip | MB7 panel tripped (1/0) |
| 736 | Diag_Chamber | PL1 chamber pressure kPa x10 |
| 737 | Diag_Fault | PL3 overcount fault (1/0) |
| 740 | IG3_Locked | IG3 beacon locked (1/0) |
| 745 | Unlock_Word | bitfield of currently unlocked challenges |

Gated text blocks read as zeros until you complete that challenge, and go back to zeros when the 20 s success window ends.
