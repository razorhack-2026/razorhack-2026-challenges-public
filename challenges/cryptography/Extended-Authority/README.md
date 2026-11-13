# Extended Authority

**Category:** Cryptography
**Difficulty:** Medium
**Author:** Lt. Rico Kopernicus

## Description (what the competitor will see)

Central Command swears its fleet directives can't be faked - every order carries a
"Directive Authentication v1" checksum, and they use a shared signing secret. It's
a fixed byte string held only by Centcom and its fleet. We believe this isn't enough.
See if you can submit a forged directive that successfully authenticates.

```
checksum = SHA256(secret || directive)
```

## Connection

A live gateway is provided at the address in the challenge's connection info (HTTP).
The homepage shows the last received directive and its checksum; submit forged directives to `POST /verify`.
