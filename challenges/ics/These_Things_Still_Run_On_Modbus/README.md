# These Things Still Run On Modbus

**Category:** ICS
**Difficulty:** Medium
**Author:** Voyager 1

## Description (what the competitor will see)

AstraTech Industries runs a fleet of autonomous DM-7 mining drones, a consignment the KEEPER OF TOMORROW is carrying to Novare. One of them is exposed on the network at
`<challenge-host>:502` — full Modbus/TCP telemetry and control, no
authentication.

Figure out what you're actually talking to, find its documentation, and
work out how to authorize its emergency destruct protocol.

## Files Provided

- None — connect directly to the Modbus/TCP service. Everything else
  needed to solve this is discoverable in-band.
