# Power-Trip — reference solution

**Flag:** `flag{P0w3r_Tr4c3r_Supr3me}`
**Category:** Cryptography (side-channel) · **Difficulty:** Hard

Correlation power analysis against an emulated Cortex-M0 running AES-128. The
competitor sets up a capture, collects a few thousand power traces off the
board, recovers its interlock key, and uses that to unseal
`dist/interlock.enc`.

## How the challenge is built

`src/firmware/` is a real bare-metal image for Cortex-M0, cross-compiled with
`arm-none-eabi-gcc` in the first Docker build stage. The AES state array is
`volatile`, so every AddRoundKey and SubBytes access is an actual load/store
rather than something the compiler can keep in registers.

`src/rig.py` runs that image under Unicorn and exposes **two devices on one
link**, wired the way a real bench is:

- **TARGET** — takes a request over its UART, runs the authentication routine,
  answers with the ciphertext. It raises a trigger GPIO around the routine and
  is otherwise unaware a scope exists.
- **SCOPE** — armed by hand, triggers on that GPIO edge, digitises `samples`
  samples starting `offset` past the trigger, at `gain` dB.

Unicorn hooks `UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE` and emits one analog sample
per data memory access — the Hamming weight of the value on the bus. Analog
noise (σ=18.0) is added ahead of the amplifier, so gain scales signal and noise
together and cannot improve SNR; it only decides how much of the ADC range gets
used.

The authentication routine is **3960 samples** long: frame staging and a CRC-16
over a 512-byte command frame fill the first ~1530, then AES-128 runs. Scope
depth is capped at **1024**, so no single capture covers the whole routine —
choosing the window is the operator's job.

Three details that matter:

- **The key schedule runs outside the trigger window.** Round keys are identical
  in every capture, so if they were inside it a competitor could average them
  out of the noise across a trace set and read their Hamming weights directly.
- **Captures are repeatable.** The noise is seeded `HMAC-SHA256(device_key,
  plaintext)`, so one plaintext always yields the same analog waveform, and
  windowing and gain are just different views of it. That blocks the shortcut of
  averaging thousands of captures of a single plaintext to erase the noise, and
  makes a dropped link resumable.
- **The rig never holds the flag.** It only knows the interlock key, and has no
  command that returns it. The flag lives in `dist/interlock.enc`, sealed under
  `SHA-256(device_key)[:16]`. Sealing under a *derived* key means an encryption
  oracle under the device key is structurally useless against the blob.

## Intended solve

**0. Read the board.** `dist/` holds only `interlock.enc`; there is no protocol
handout. The banner names both devices and warns that the routine is longer than
the scope can hold and that the power-up settings are unusable. `HELP` lists the
command set. The blob states its own container format in a plaintext envelope.

**1. Get the scope on-scale.** It powers up at -40 dB, 256 samples, offset 0. A
capture there returns 3 distinct codes — visibly dead. Raising gain to around
0 dB gives ~80 codes of healthy swing. This step is quick and forgiving: the
usable range runs from about -33 dB all the way to +40 dB, where 93% of samples
clip and CPA *still* works off the linear remainder. Gain is setup, not
difficulty.

**2. Find the cipher.** This is the real instrumentation work. Depth is 1024 and
the routine is 3960 samples, so the operator has to walk the offset and look at
what comes back. Offset 0 shows the trigger burst and the frame staging; the
CRC-16 is a long stretch of regular, low-amplitude activity; AES starts near
1530 and has visible round structure. Measured, at 3000 traces:

| offset | 0 | 512 | 1024 | 1400 | 1600 | 1800 | 2200 | 3000 |
|---|---|---|---|---|---|---|---|---|
| bytes | 0/16 | 0/16 | 16/16 | 16/16 | 16/16 | 5/16 | 0/16 | 0/16 |

The window has to contain the round-1 S-box leak at **sample 1643**. Anything
from ~1024 to ~1650 works; past that it falls off a cliff.

**3. Bulk capture.** `BATCH <n>` runs n armed requests at the current settings,
which is the only practical way to collect thousands. ~53s for 6000.

**4. CPA.** Standard first-round attack. For each key byte and each of 256
guesses, correlate `HW(SBox(p ⊕ k))` against every sample; the correct guess
peaks. Partial recovery is the signal to capture more, not that the attack is
broken.

**4b. Key enumeration.** Do not throw away a near-miss. Near the threshold the
true byte routinely places second to sixth rather than first, and the blob's
known header is a free oracle for testing a candidate key. `solve.py` keeps the
top 6 candidates per byte and walks the combinations in increasing order of
total correlation penalty, cheapest first. Measured on three 3000-trace sets
that CPA alone got 12/16, 15/16 and 14/16:

| top-1 bytes | candidates tried | time |
|---|---|---|
| 12/16 | 12529 | 0.3s |
| 14/16 | 10 | 0.0s |
| 15/16 | 4 | 0.0s |

That drops the practical trace requirement from ~6000 to ~3000, and it is
standard CPA practice rather than a trick.

**5. Unseal.** The blob's envelope gives the recipe: derive `SHA-256(key)[:16]`,
AES-128-CBC decrypt the payload after the `--` line with its leading 16 bytes as
IV. A correct key produces the `RPC-INTERLOCK-AUTH` header; the flag is on the
`auth:` line.

```bash
python solution/solve.py        # defaults: gain 0dB, 1024 samples, offset 1600
```

## Verified

Run against the live container on 2026-09-14:

```
[*] SCOPE samples=1024 offset=1600 gain=0dB depth_max=1024
[*] capture took 53.1s
[*] 6000 traces x 1024 samples
[*] CPA in 5.4s
[*] per-byte peak correlation 0.078 .. 0.118
[*] interlock key = 173ccb58a286a5b4794fe05480cecf5e
FLAG: flag{P0w3r_Tr4c3r_Supr3me}
```

~60s end to end once the scope is set up correctly. The runtime is not the
difficulty — finding the window is.

## Difficulty calibration

Bytes recovered by **CPA alone** (top-1, no enumeration), at gain 0 dB,
offset 1600, depth 1024:

| traces | 1000 | 2000 | 3000 | 4000 |
|---|---|---|---|---|
| σ=14 | 8/16 | 16/16 | 16/16 | 16/16 |
| **σ=18 (shipped)** | 0/16 | 12/16 | 15/16 | **16/16** |
| σ=22 | 0/16 | 2/16 | 9/16 | 13/16 |

**Read that table with care — it was measured one trace set per cell, and the
variance at the knee is larger than the table suggests.** A live 4000-trace run
returned 15/16, and three independent 3000-trace runs returned 12/16, 15/16 and
14/16. Disjoint-subset retests put reliable top-1 recovery at 4000–5000, not
4000 flat.

With key enumeration the practical requirement is ~3000. `solve.py` defaults to
6000 anyway, so the reference solve has margin and a reviewing GM never sees a
coin flip.

`ANALOG_NOISE` in `src/rig.py` is the difficulty dial. Re-run the sweep if it or
the firmware changes — note that changing the firmware also moves the offset the
window has to land on, and measure several subsets per point rather than one.

## Where competitors will stall

In rough order of likelihood:

1. **Never changing the offset.** An offset-0 capture looks perfectly healthy —
   it has a trigger burst and plenty of activity — but it contains the CRC, not
   the cipher. CPA on it returns nothing, and it reads as a broken attack rather
   than a wrong window. This is the intended hard step.
2. **Giving up on a near-miss.** 12/16 bytes looks like failure if you expect
   all-or-nothing. It is roughly 0.3 seconds of key enumeration away from the
   flag, and capturing more traces also fixes it.
3. **Scripting the capture without re-configuring the scope.** Settings are
   per-connection — each link is its own forked `rig.py` — so a script that
   explored successfully by hand and then connects fresh gets the power-up
   state back. The signal is loud (256 samples instead of 1024, 3 distinct
   codes, values spanning -1..1, and the banner says so on every connect), but
   it is worth a few minutes of confusion. This is also the authentic pattern:
   a real ChipWhisperer script sets gain, samples and offset at the top of
   every run, because connecting re-initialises the scope.
4. **Leaving gain at the floor.** A 3-code trace is obviously wrong, so this one
   is usually self-correcting within a couple of captures.
5. **One connection per capture** instead of `BATCH`, which makes collection
   slow enough to look infeasible.

## Deployment notes

- **One instance per team**, but **every instance must run the same
  `DEVICE_KEY`** — `challenge.yml` carries a single static flag, so per-team keys
  would need per-team flags.
- `DEVICE_KEY` and `dist/interlock.enc` are a matched pair. Overriding the key
  without regenerating the blob (`src/gen_interlock.py`) makes the challenge
  unsolvable.
- The image contains `device_key.txt`, as any service image must contain its
  secret. It is not reachable through the protocol; protect it the usual way, by
  not handing out image or shell access.
- Each connection is its own forked `rig.py` on a pty, capped at 50k requests,
  with `max-children=16`. A full solve costs ~35s of container CPU.
