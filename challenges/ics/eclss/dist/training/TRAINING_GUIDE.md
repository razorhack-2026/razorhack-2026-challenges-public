# Training Bay - Player Guide

Fifteen short warm-ups that teach the three tools the main ECLSS challenge is
built on: **Modbus**, **OpenPLC** logic, and the **Ignition** HMI. Do these
first; every skill here shows up again on the ship.

| What | Where |
|------|-------|
| Training PLC (Modbus TCP, unit id 1) | `tcp://<host>:5020` |
| Training HMI (Ignition Perspective) | `http://<host>:8088/data/perspective/client/training` |
| Register map | `REGISTER_MAP.md` (this folder) |
| PLC source code | `TRAINING_LOGIC.st` (this folder, secret constants redacted) |
| New to Modbus? | `MODBUS_PRIMER.md` (main docs) |

Flags look like `flag{...}`. Text flags are ASCII packed two characters per
register, **low byte first**. Successful challenges stay unlocked for about
**20 seconds** and then re-arm, so read your flag promptly - and if the rig
looks stuck, a teammate may be mid-attempt; wait a few seconds.

`<host>` is your team's own copy of the rig: press **Start** on any ICS
challenge in CTFd, and its connection info shows the host. **Stop** resets it.

---

## Modbus

### MB1 - Roll Call
Every bay reports its ID in the very first holding register. The flag is
`flag{...}` with that number, in decimal, inside the braces.

### MB2 - Long Read
Somewhere in holding registers 10-25 the bay is saying something. Read the
whole block in one request and decode it.

### MB3 - The Vendor Manual
The vendor manual says: *"The maintenance banner begins at register 40201."*
The manual uses old Modicon numbering. Translate it to a plain 0-based
holding-register address and read the banner.

### MB4 - Light the Beacon
Coil 0 commands the navigation beacon. Turn it on; while it is lit the PLC
publishes a message at holding registers 300-315. The beacon switches itself
off after 15 seconds.

### MB5 - Big Number
Holding registers 400-401 hold one **32-bit unsigned integer**, high word
first. Flag: `flag{...}` with the value, in decimal, inside the braces.

### MB6 - Floating Point
Holding registers 410-411 hold one **IEEE-754 single-precision float**, high
word first. Flag: `flag{...}` with the value, to exactly 3 decimal places, inside the braces.

### MB7 - Breaker Panel
Holding register 1025 is a panel of 16 breakers, one per bit. Bits count from
0 at the least significant end: bit 0 has the value 1. Close **breaker 9**
(set bit 9) and leave every other breaker exactly as you found it. Change anything else and the panel trips; coil 30 resets a tripped panel.
The flag appears at holding registers 700-715.

## OpenPLC logic

For these, open `TRAINING_LOGIC.st` and read the function block named in each
challenge. The code tells you *what* the PLC wants; the register map tells
you *where* to write it. The PLC scans every **100 ms** - keep that in mind.

### PL1 - Airlock Cycle  - `FB_Airlock`
Cycle the airlock so the outer door opens. Coils 8-11 are your inputs. Watch
holding registers 734 (door) and 736 (chamber pressure). Flag at 600-615.

### PL2 - Hold to Confirm  - `FB_HoldTimer`
A confirm button on coil 16 has to be held. How long, and what happens if you
let go early? Holding register 731 shows how long it has been held. Flag at
620-635.

### PL3 - Count the Pulses  - `FB_PulseCounter`
Send exactly the right number of pulses on coil 17. Holding register 730
shows the count, 737 shows a fault. Coil 18 resets. Flag at 640-655.

### PL4 - Motor Starter  - `FB_MotorSealIn`
Start the motor and leave it running on its own. Coils 24 (START) and 25
(STOP) are the pushbuttons. Read the comments about how each button is wired.
Holding register 732 shows whether the motor runs. Flag at 660-675.

### PL5 - Four to Twenty  - `FB_Scaling`
A level transmitter sends 4-20 mA to the PLC's analog input, which you can
write at holding register 1024. Make the tank read **62.5 %** and hold it.
Holding register 733 shows the scaled level (x10). Flag at 680-695.

## Ignition

### IG1 - Who Are You?
Every Ignition gateway has a system name. Find this one's **without logging
in**. Flag: `flag{...}` with the gateway name inside the braces.

### IG2 - Hidden in Plain Sight
Open the Training HMI. Something on that screen was not meant to be seen.

### IG3 - Tune the Beacon
Use the Training HMI to tune the deep-space beacon. The screen tells you the
frequency in the form of a clue. When the PLC confirms the lock, the HMI
shows your flag for 30 seconds.

---

**Rules of the bay:** stay on the two services above. Don't hammer the PLC
with thousands of writes per second - you won't need to, and it slows the
rig down. If something seems broken, ask staff before assuming it is
part of the puzzle.
