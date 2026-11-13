# Coremelt: Core — reference solution + full-chain writeup (GM only)

**Scores:** the OT flag emitted by the PLC over Modbus. **Part 4 of 4 (final).**
This is the master writeup for the whole Coremelt chain; parts 1–3 have their
own short writeups.

**One-line chain:** unauthenticated React2Shell RCE on CoreWatch → loot + offline
hash crack + decrypt an engineer memo → SSH pivot into the OT workstation with
the reused credential → reverse the PLC ladder gate → drive the live PLC over
Modbus to emit the final flag.

## Deploy

The whole chain is one two-container stack in
`challenges/web/coremelt/`:

```
cd challenges/web/coremelt && ./build.sh
```

- `corewatch-web` — the vulnerable Next.js app, only player-facing port 3000
- `eng-ws` — SSH + soft-PLC (Modbus/TCP 502) in the web container's network
  namespace, bound to **127.0.0.1 only**, no host ports; reachable only through
  the web container

Per-team instances are recommended (both the RCE box and the PLC state are
player-mutable). Reset PLC registers/coils and restore project state on the
web app's reap cadence.

## Full chain

### Stage 0 — fingerprint (decoy)
`GET /` serves the CoreWatch reactor dashboard (flavour; controls are inert).
Its Engineering/RTU/Admin nav links (`/admin`, `/engineering`, `/rtu`, ...) all
return HTTP 404 — looks like a Next.js middleware auth gate (CVE-2025-29927) but
it's a **decoy** with no console behind it. Real bug is on the server-action POST
path to `/`. Fingerprint: `next@15.0.3` / `react@19.0.0`.

### Stage 1 — React2Shell RCE (CVE-2025-55182) → **C1 flag** `/flag.txt`
Vulnerable RSC "Flight" deserializer. Multipart server-action request →
prototype-chain traversal to the global `Function` constructor → JS eval in the
server process. `value` = `{"then": "$B0"}`, `_formData.get` =
`$1:constructor:constructor`, `_prefix` = the JS body; field `1` = `"$@0"`;
headers `Next-Action` + `Accept: text/x-component`. In-scope subtleties:
`process.mainModule.require` (no lexical `require`), and error-based exfil via a
`NEXT_REDIRECT` `digest` (no egress needed). See `solution/exploit_react2shell.py`.

### Stage 2 — loot + crack + decrypt → **C2 flag** (engineer memo)
`/app/corewatch.db`: `users` (only `j.reyes` cracks → `supernova1`, rockyou line
84072; the other two hashes are random) and `rtu_secrets` (an
`openssl enc -aes-256-cbc -pbkdf2` blob, base64 head `U2FsdGVk`). Crack the hash,
decrypt the blob with it → the memo carries the C2 flag. The plaintext memo is
never in the image. Breadcrumb `/app/.env` → `PLC_WS_HOST=127.0.0.1`.

### Stage 3 — SSH pivot → **C3 flag** `~/flag.txt` on eng-ws
`eng-ws` is loopback-only; SSH to `127.0.0.1` from inside the foothold, log in as `j.reyes`
with the reused password. `~/flag.txt` is the C3 flag. Non-interactive password
auth: `SSH_ASKPASS_REQUIRE=force` (OpenSSH ≥ 8.4).

### Stage 4 — reverse the ladder gate, drive the PLC → **C4 flag (scores here)**
Pull `~/plc_project/coremelt_gate.st` (ciphertext only). `PROGRAM maint_override`
is a reactor maintenance-override interlock. A 64-bit key (four holding registers
`%QW0-3`) is folded word-by-word against a stored signature `SIG[]` through:

- S-box substitution (`SCRAMBLER`),
- odd-modular multiply (undo needs a **modular inverse**),
- fixed rotate, then fixed add,
- CBC chaining across the four words (IV baked in).

Every step is a bijection, so exactly one 64-bit trigger matches `SIG[]`; the
64-bit width makes it **un-brute-forceable over Modbus** — reverse it offline.
On a correct trigger the PLC derives an S-box keystream **keyed on the trigger
bytes** and XORs it over `OVERRIDE_PAYLOAD` (baked ciphertext) into the readback
registers — so reading the `.st` without recovering the trigger yields nothing.

Invert it (see `solve_gate()` in `solution/solve.py`, or the stage-4-only
`solution/solve_engws.py`): recover the trigger from `SIG[]`, then drive the live
PLC over Modbus (through the web container — `127.0.0.1:502` is loopback-only; the solver
pushes `solution/mb_drive.py`, a stdlib Modbus client):

- write `[0,0,0,0]` → `GATE_OPEN=0`, readback empty (nothing free on the wire)
- write the recovered trigger → `GATE_OPEN=1`, **C4 flag** in registers 10+

## Verify (author-solve from the live instance)

```
cd solution && python3 solve.py <host> 3000
```

Drives all four stages and prints `ACCEPTANCE: PASS — 4/4 flags recovered`,
asserting the four flags are distinct and the gate opens only on the trigger.
`solution/solve_engws.py <recovered.st> <plc_host> 502` is the stage-4-only
acceptance test.

## Not trivially solvable another way

- The middleware decoy has no route behind it.
- Only `j.reyes` cracks; the memo is ciphertext-only in the image.
- The C3 flag lives on a separate container — needs the real SSH pivot.
- The 64-bit gate blocks Modbus brute-force; the flag keystream is trigger-keyed,
  so a shell on `eng-ws` without the RE still yields nothing.

## Per-team variation

Rotating one S-box seed in the gate generator changes both the gate and — through
the keystream — the flag binding, so a mid-event writeup can't leak a static
answer.

## AI-solvability (by design, medium)

The chain is AI-solvable end to end (known CVE, known crack, documented gate) —
that's expected for a medium. The human-facing kill chain and OT pivot are the
value; read-the-program RE can't be made AI-proof.
