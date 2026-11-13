# Overburden: Master Loop

**Category:** Pwn
**Difficulty:** Hard
**Author:** Andy Roid

## Description

You reached ICARUS's extraction gateway -- the field RTU that fronts the
extraction master deeper in the plant. The gateway will let you *read* the
master's telemetry, but it won't let you touch the process. The master holds
the maintenance key, and it only surrenders it once the extraction loop is
brought to a safe state -- in the right order, respecting its interlocks.

Get through the gateway, reach the master, and shut the loop down safely.

Connect to the extraction gateway (raw TCP, custom binary protocol):

```
nc <host> <port>
```

## Files Provided

- `rtu_gateway` — the gateway firmware image (stripped)

The master is not provided, and no flag lives in the gateway — the key only
comes from the live plant.
