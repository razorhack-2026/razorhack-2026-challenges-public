# Overburden

**Category:** Pwn
**Difficulty:** Hard
**Author:** Andy Roid

## Description

ICARUS's extraction plant still has a field controller answering on the wire,
and its firmware (fw 1.1.0) predates anyone caring about security — it trusts
whatever length you tell it. But the maintenance interface wants a session key
first. Talk to it, reverse the firmware, and make the RTU run the one routine it
should never let you reach: the handler that coughs up its key.

Note: the firmware file alone won't get you there — the RTU only surrenders what
it hands you *on the wire*. You have to work the live device.

Connect to the field RTU (raw TCP, custom binary protocol):

```
nc <host> <port>
```

## Files Provided

- `rtu_server` — the RTU's firmware image (stripped)

No flag lives in the firmware — it only comes from the live device.
