# Power-Trip

**Category:** Cryptography
**Difficulty:** Hard
**Author:** Voyager 2

## Description (what the competitor will see)

RazerPowerCo burned the reactor-interlock key into OTP on every controller board it shipped —
no read-back, no debug port, nothing on the wire. Salvage pulled one off the derelict and wired
it into a bench rig.

The board's UART will encrypt anything you hand it, and the rig answers `HELP`. It will not tell
you the key. But the rig's shunt amplifier is still wired in, and it reports exactly what the
chip drew while it worked.

`interlock.enc` came off the same controller.

## Files Provided

- `interlock.enc` - sealed authorisation record pulled off the same controller

The bench rig is live at the address on the challenge page. It answers `HELP`.
