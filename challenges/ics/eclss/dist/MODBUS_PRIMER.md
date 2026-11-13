# Modbus in 10 minutes (for players)

You don't need prior OT/ICS experience for this challenge. Here's everything
about Modbus you need to start.

## What Modbus is

Modbus is a dead-simple protocol for reading and writing numbers on industrial
equipment (PLCs, sensors, drives). A PLC acts as a **server** (historically
"slave"); your tool is the **client** ("master"). You connect over TCP to port
**502** (the Training Bay PLC uses **5020**), name a **unit id** (here: `1`), and
ask for values by **address**.

## The four data areas

| Area | Size | Read? | Write? | Function codes |
|------|------|-------|--------|----------------|
| Coils | 1 bit | yes | yes | read 1, write 5/15 |
| Discrete inputs | 1 bit | yes | no | read 2 |
| Input registers | 16-bit | yes | no | read 4 |
| **Holding registers** | 16-bit | yes | yes | read 3, write 6/16 |

This challenge lives almost entirely in **holding registers** (telemetry,
setpoints, and the flag text) plus a few **coils** (on/off commands). The
Training Bay comes with a register map (`training/REGISTER_MAP.md`), and so
does the ship (`eclss/REGISTER_MAP_PLAYER.md`): its telemetry, setpoints and
commands. The ship's map isn't complete, though: finding the rest is part of
the challenge.

## Gotchas that trip people up

- **Scaling.** A register is a whole number 0-65535 (or -32768..32767 signed).
  Fractional values are pre-multiplied. 12.34 % is stored as `1234`
  ("x100"); 40.0 % is `400` ("x10"). Divide to read, multiply to write.
- **Addressing base.** Some tools number registers from 0, some from 1, and
  some prefix the data area (e.g. `40001` = first holding register). This
  challenge uses plain **0-based** addresses: holding register `0` is the
  first one. If your reads look off by one, that's why.
- **Signed vs unsigned.** Values here are signed 16-bit, but most tools
  (pymodbus included) hand them back unsigned, so `65535` really means `-1`.
  Only a few diagnostic values ever go negative.
- **Text in registers.** ASCII is packed two characters per register, **low
  byte first**. Register value `27750` = `0x6C66` = bytes `0x66 0x6C` = `"fl"`.

## Tools

Pick one; all three are fine.

### mbpoll (command line)
```bash
# read 17 holding registers starting at 0 (0-based), unit id 1
mbpoll -m tcp -a 1 -r 1 -c 17 -t 4:hex <host>       # -r is 1-based here!
```
`<host>` is the host in your challenge's connection info. mbpoll is 1-based, so
register 0 is `-r 1`. Mind the off-by-one.

### pymodbus (Python - recommended)
```bash
pip install -U pymodbus      # on Kali, inside a venv
```
```python
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient("<host>", port=502); c.connect()   # Training Bay: port=5020

# read 10 holding registers starting at 0
r = c.read_holding_registers(0, count=10, device_id=1)
print(r.registers)

# write 42 to holding register 1100 (an example address - pick your own)
c.write_register(1100, 42, device_id=1)

# read coils 0-7, then turn coil 5 on (example addresses again)
print(c.read_coils(0, count=8, device_id=1).bits)
c.write_coil(5, True, device_id=1)
c.close()
```
> `device_id=` is the keyword on **pymodbus 3.10 and newer**. On 3.0-3.9 it is
> `slave=` instead (3.7, for example, rejects `device_id=` with a TypeError),
> and on 2.x it is `unit=`. Check yours with
> `python3 -c "import pymodbus; print(pymodbus.__version__)"`.

### Decoding packed ASCII text
```python
def text(c, start, count=16):
    regs = c.read_holding_registers(start, count=count, device_id=1).registers
    b = bytearray()
    for v in regs:
        b += bytes([v & 0xFF, (v >> 8) & 0xFF])
    return b.split(b"\x00")[0].decode("ascii", "replace")

print(text(c, 0))   # 0 = the first register of the block you found
```

That's the whole toolkit. Start by reading the holding registers and seeing
what the ship is telling you.
