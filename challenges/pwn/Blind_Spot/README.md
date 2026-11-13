# Blind Spot

**Category:** Pwn
**Difficulty:** Hard
**Author:** Voyager 1

## Description (what the competitor will see)

RazorPower Co.'s habitat ring aboard the KEEPER OF TOMORROW has a coolant loop controller on Modbus/TCP
at `<challenge-host>:502`, no authentication. Read its holding registers
and you'll find the valve position and coolant flow rate it runs the loop
on; both are writable.

It isn't the only station on that segment. A separate watchdog polls the
controller directly and forces an emergency reset whenever the valve or
flow reading leaves its safe operating band. The watchdog runs no service
of its own and has nothing to log into. It only reads, and it counts a
missed or blocked poll as a fault the same as an out-of-range one, so
blinding it or cutting its link to the controller gets you nowhere: the
controller won't release anything unless the watchdog is actively
reporting good readings the whole time.

Push the loop outside its safe band and hold it there long enough for the
controller to react, without the watchdog ever reading a bad value off
the wire.

A jump box is provided on the same network segment as the controller and
the watchdog. SSH in with the credentials below; it has passwordless sudo
and a standard set of network tools
(`nmap`, `tcpdump`, `nano`, and Python with `scapy` and `pymodbus`)
preinstalled:

```
ssh player@<challenge-host> -p 2224
password: bl1ndsp0t
```

## Files Provided

- None. Everything you need is reachable live from the jump box on the
  provided network segment (`10.13.37.0/24`).
