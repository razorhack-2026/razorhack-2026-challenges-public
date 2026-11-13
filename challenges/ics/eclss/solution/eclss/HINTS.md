# Tiered Hints (organizer-controlled)

Three tiers per challenge: **nudge** (free / early), **bigger** (mid-game), and
**near-spoiler** (last resort, usually behind a point cost on CTFd). Release
them on a timer or let teams unlock at a penalty. Flags themselves are in
`SOLUTIONS.md`, never here.

---

## 1. Hailing frequencies (recon)

- **Nudge:** Not every holding register is a sensor. Read a wide block and look
  at the raw numbers, not just the decoded engineering values.
- **Bigger:** One region's values all fall in the printable-ASCII range. Two
  characters live in each 16-bit register.
- **Near-spoiler:** Read holding registers starting at 1124 and unpack each as
  two bytes, low byte first. See the primer's decode snippet.

## 2. The ghost deck (HMI)

- **Nudge:** The HMI menu is not the whole gateway. Pages can exist without a
  menu link, and your browser is still told about them.
- **Bigger:** Open the browser's developer tools, Network tab, and reload the
  HMI. The response for `project/eclss` describes the whole project:
  look at `pageConfig.pages`.
- **Near-spoiler:** Browse to `/data/perspective/client/eclss/crew-manifest`
  on the gateway (port 8088).

## 3. Breathe easy (O2)

- **Nudge:** Oxygen is below its floor. Find the O2 setpoint among the
  setpoint registers and compare it to what "normal" air should be.
- **Bigger:** Something keeps writing the setpoint back down every so often.
  Fix it, but expect it to fight you until challenge 6.
- **Near-spoiler:** Write 2095 to holding register 1024 (O2 setpoint, 20.95%).
  Watch HR0 climb into the 19.5-23.5% band and HR14 bit0 set.

## 4. Scrub it out (CO2)

- **Nudge:** CO2 removal uses two beds that should take turns. Right now one
  bed is doing all the work and saturating.
- **Bigger:** There's a CDRA mode register next to the bed swap time. One value
  means "auto swing," the others pin a single bed. A one-off fix won't get CO2
  under 5000 while the maintenance sync is armed: keep AUTO restored for a few
  minutes, or disarm first (challenge 6). A regen-heater coil speeds it up.
- **Near-spoiler:** Set holding register 1026 to 1 (CDRA AUTO) and turn coil 1
  on (regen heater). CO2 falls back under 5000 ppm; HR14 bit1 sets. If CO2
  has been climbing for a while it can take a couple of minutes to come
  down - the beds remove it at a fixed rate. Be patient, not creative.

## 5. Goldilocks (temperature)

- **Nudge:** The cabin is hot because it's being told to be. Find the
  temperature setpoint.
- **Bigger:** The temp setpoint is scaled x100 and is sitting far above a
  comfortable cabin value.
- **Near-spoiler:** Write 2250 to holding register 1028 (22.5 C). HR2 returns
  to the 18-27 C band; HR14 bit2 sets.

## 6. Exorcise the maintenance sync (root cause)

- **Nudge:** Your fixes keep getting undone. Something is re-applying a
  baseline on a timer. The HMI knows how to stop it.
- **Bigger:** There's a maintenance procedure that isn't on the menu. It names
  a code and the register to write it to. Don't guess the code - find it.
- **Near-spoiler:** Open `/data/perspective/client/eclss/maint` on the gateway,
  read the disarm code, and write it to holding register 1030. Five wrong
  codes lock the register for 60 seconds, so get it from the page.

## 7. All systems nominal (capstone)

- **Nudge:** Once the sync is disarmed, your good setpoints finally stick. Now
  keep everything calm.
- **Bigger:** The PLC wants a continuous stretch with zero alarms (holding
  register 10 == 0). Watch the "nominal hold" counter climb.
- **Near-spoiler:** Hold O2, CO2, and temp in range with HR10 == 0 for 30
  seconds straight. HR14 bit4 sets and the capstone flag unlocks at HR1224.
