# ECLSS - Player Briefing

> Scenario (fiction): you are on the deck crew of the **ISV Ozark Horizon**.
> Mid-transit, the Environmental Control & Life Support System (ECLSS) started
> fighting the crew: oxygen sagging, CO2 climbing, the cabin running hot. The
> watch officer swears nobody touched the setpoints. Get the cabin back to
> nominal and figure out what keeps undoing your fixes.

**Targets** (`<host>` is your team's own copy: press **Start** on any ICS
challenge in CTFd, and its connection info shows the host)

| System | Address |
|--------|---------|
| ECLSS PLC (Modbus TCP) | `tcp://<host>:502`, unit id 1 |
| Ignition HMI (Perspective) | `http://<host>:8088` |

Flags look like `flag{...}`. There are **seven**. You do not need to break
anything physical or off-range - everything you need is on those two services.
Work the PLC with any Modbus client (mbpoll, pymodbus, a Metasploit module,
your own script). Registers are 16-bit signed; scaled values are stored x10 or
x100.

---

## 1. Hailing frequencies  (recon)

Point a Modbus client at the PLC and sweep the holding registers. Most carry
telemetry and setpoints - but one block spells something out in ASCII. Read it.

*Hint: two ASCII characters pack into each 16-bit register, low byte first.*

## 2. The ghost deck  (HMI)

The HMI's menu shows a single screen. The gateway is hosting more pages than
the menu admits to - one was "retired at launch" but never actually removed.
Find the page that nothing links to.

*Hint: the menu only decides what gets linked. Reload the HMI with your
browser's developer tools open on the Network tab. One request is named after
the project: open its response and look for the list of pages.*

## 3. Breathe easy  (oxygen)

Oxygen is below the 19.5% floor and the generator is not keeping up. Something
keeps dragging the O2 setpoint down. Get cabin O2 back into the 19.5-23.5%
band and hold it there. The PLC will publish a flag once O2 is in range.

*Hint: the HMI shows the O2 setpoint's current value - find the same number
in the PLC's holding registers. As in the Training Bay, the registers you
can write start at 1024. Once bit 0 of holding register 14 sets, the flag
text appears near the ECLSS 1 banner.*

## 4. Scrub it out  (CO2)

CO2 is climbing past the alarm ceiling (5000 ppm). The CO2 removal assembly
(CDRA) has two adsorption beds that are supposed to swing back and forth so one
regenerates while the other scrubs. Right now it is pinned to one bed. Restore
the swing so CO2 comes back into range.

One fix won't hold: the maintenance sync re-pins the scrubber every 20 s,
and CO2 falls far more slowly than that. Keep the swing restored for a few
minutes, or stand the sync down first (ECLSS 6).

*Hint: the HMI shows the scrubber's mode and how often the beds swap. The
swap time is a plain number in the PLC's holding registers (as in the
Training Bay, the ones you can write start at 1024), and the mode sits right
next to it. The mode is a number from 0 to 3, and the HMI's scrubber label
changes as soon as you write one, so you can tell when the swing is back.
Once bit 1 of holding register 14 sets, the flag text appears near the ECLSS
1 banner.*

## 5. Goldilocks  (temperature)

The cabin is drifting hot. The thermal setpoint has been pushed well above
comfort. Bring the cabin temperature back into the 18-27 C band.

*Hint: the HMI shows the temperature setpoint's current value - find the
same number in the PLC's holding registers. As in the Training Bay, the
registers you can write start at 1024. Once bit 2 of holding register 14
sets, the flag text appears near the ECLSS 1 banner.*

## 6. Exorcise the maintenance sync  (root cause)

You have probably noticed your corrections getting undone every so often. A
"maintenance sync" routine re-applies a commissioning baseline while it is
**armed**. There is a documented way to stand it down: a maintenance console
on the HMI explains it and gives you the code (it isn't on the menu either:
ECLSS 2's hint shows how to find pages like it). Writing that code to the right
register disarms the routine for good.

*Careful: five wrong codes in a row lock the register for a minute. This is a
reasoning puzzle, not a number to brute force.*

## 7. All systems nominal  (capstone)

With the sync disarmed and O2, CO2, and temperature all in range, hold the
cabin nominal. Once the environment has been clean and stable continuously for
long enough, the PLC releases the final flag.

---

### Scoreboard of objectives

The PLC keeps a live bitfield at **holding register 14** (`FlagsEarned`):

| bit | meaning |
|-----|---------|
| 0 | O2 in range |
| 1 | CO2 in range |
| 2 | temperature in range |
| 3 | maintenance sync disarmed |
| 4 | full nominal hold achieved |

Watch it climb as you bring the ship back.
