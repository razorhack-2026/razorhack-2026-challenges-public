# Silent Directive — Reference Solution (GM only)

**Category:** ICS · **Difficulty:** Medium · **Flag:** `flag{s7comm_write_var_is_a_trust_boundary}`

## Summary
A realistic S7comm factory capture (~1280 packets / ~2.3 min): TCP + COTP + S7
Setup Communication, then heavy cyclic **Read Var** polling of live telemetry
(DB2) from two stations. Four **Write Var** commands are buried in that stream.
The Professor's shim (`interceptor.py`) re-encodes the *value* of each write
with a keystream; the telemetry reads are plaintext. Recover the 16-byte key
from the operator console's known-plaintext setpoint writes, then decrypt the
one covert write.

## Files (dist/)
- `extraction_bus.pcap` — the capture (values of Write Vars are ciphertext).
- `interceptor.py` — the shim; documents the keystream and the DB1 layout. No key.
- `workstation_console.log` — operator-sanctioned DB1 setpoints (known plaintext).

## Intended path
1. **Isolate the commands.** In Wireshark the bus is S7comm on TCP/102. Filter
   the reads out: `s7comm.param.func == 5 && s7comm.header.rosctr == 1` leaves
   **4 Write Var requests** — three to **DB1** (operator setpoints), one to
   **DB7** (odd block, ~4x larger). The DB7 write has **no console entry**.
2. **Read the shim.** `interceptor.py`: each value byte `i` is
   `plain[i] ^ key[i%16] ^ stream[i]`, where `stream` is a glibc LCG
   (`s = s*1103515245 + 12345 mod 2^31`, byte = `(s>>16)&0xff`) seeded from
   `pduref ^ 0x5350`. `pduref` is the S7comm PDU reference of that frame (in
   the capture). This is **not** repeating-key XOR: the per-frame stream makes
   every frame's keystream unique and non-repeating, so single-packet frequency
   analysis fails.
3. **Recover the key.** For each DB1 write, `workstation_console.log` gives the
   sanctioned record; pack it big-endian to 32 bytes (8 × u32 in the documented
   field order). Then `key[i%16] = cipher[i] ^ plain[i] ^ stream_i`. One 32-byte
   write already covers all 16 key positions; the three cross-check.
4. **Decrypt DB7.** Apply the recovered key + the DB7 frame's stream to its
   ciphertext → Dr. Rootkit's directive. The flag is inside.

## Alternate path (also valid)
Crib-dragging known substrings (e.g. `OVERRIDE`, `flag{`) against the DB7 write
leaks `key[i%16]` at those offsets too — still requires understanding the
`key ^ stream` structure from the shim. Not a cheese.

## Non-shortcuts (verified)
- `dist/` contains no flag, key, or directive plaintext (grep + byte scan).
- Telemetry reads are randomized live values, not the setpoints, so they don't
  leak a plaintext/ciphertext pair for the key.

## Run
```
python3 solution/solve.py
```
Recovers the key `9c1f4ab7d0e35286a4f7c9130b6e57d2` and prints the flag.
