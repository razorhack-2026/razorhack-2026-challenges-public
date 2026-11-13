# Glossolalia -- Solution

**Answer (this reference build):**
- nam-shub / input phrase: `the_nam_shub_of_enki_severs_babel`
- flag: `flag{sp34k_th3_nam_shub_and_babel_falls}`

Official solver: `solution/solve.py` (recovers both from `asherah.nam` alone, then
confirms through the real `enkivm`). Run `make verify`.

---

## 0. Recon

Two files: `enkivm` (a small ELF) and `asherah.nam` (553 bytes). Running it just
consumes stdin and, for the wrong input, prints nothing:

```
$ printf 'hello' | ./enkivm asherah.nam
$            # silence == rejected
```

`strings enkivm` shows no `flag{`, but it does show `unknown rune 0x%02x at %u`,
`the tongue loops forever`, `not a nam-shub` -- the language of an **interpreter**.
`strings asherah.nam` shows nothing readable. So the flag is not sitting in a file;
it's produced by running the right input through this VM.

## 1. Reverse `enkivm` (recover the ISA)

`enkivm` is a classic fetch/decode/execute loop. What you recover:

- **State:** 8 registers (32-bit), a program counter, a 4 KB byte **tape**, a zero
  flag.
- **`.nam` format:** header `magic "NAM\0"`, `code_len` (u16 BE), `data_len` (u16 BE),
  then `code`, then `data`. The `data` bytes are copied into the tape at offset 0.
- **Instructions are fixed 4 bytes:** `[op][a][b][imm]`.
- **16 opcodes**, and the byte values are *not* 0..15 -- you must build the map. In
  this build they are: `HALT=0x00 LOADI=0x11 MOV=0x22 ADD=0x33 SUB=0x44 XOR=0x55
  AND=0x66 MIX=0x77 LOAD=0x88 STORE=0x99 CMP=0xAA JMP=0xBB JZ=0xCC JNZ=0xDD IN=0xEE
  OUT=0xFF`.
- Most ops are ordinary (`LOADI`, `MOV`, arithmetic, `LOAD/STORE` on the tape,
  `CMP`, jumps, `IN` reads the next stdin byte, `OUT` emits a byte). The one that
  matters: **`MIX Ra` does `Ra = tape[Ra & 0xFF]`** -- a lookup into the first 256
  bytes of the tape. Those 256 bytes are an **S-box** (they arrive in `data`).

## 2. Disassemble `asherah.nam`

With the opcode map, decode the code section (54 instructions). It is two loops
plus setup. Structurally:

**Setup** builds two tape addresses (`256` and `512`) by doubling `0x80`, then loads
the constants: `K1 = 0xb7` into a register, `roll = K2 = 0x6c`, an index
accumulator `= 0`, and the loop counter `i = 0`.

**Loop 1 (read + transform + compare)** for each input byte:
```
IN   -> in[i]
STORE in[i] at tape[512 + i]          # stash the raw input for later
Ra = in[i] + acc                      # acc accumulates i*K1
Ra ^= roll
MIX Ra                                # Ra = SBOX[Ra & 0xFF]  == t[i]
compare Ra with tape[256 + i]         # target[i]
if not equal -> HALT (silent reject)
roll = t[i]
acc += K1
i   += 1
```

**Loop 2 (decrypt + output)**, reached only if all bytes matched:
```
for j in 0..M-1:
    OUT  tape[289 + j]  XOR  tape[512 + (j mod N)]
```
i.e. `flag_ct[j] XOR input[j mod N]`.

**Tape / data layout** (from the addresses used): `SBOX @ 0..255`,
`target @ 256..256+N-1`, `flag_ct @ 256+N..`, and the raw input is stashed at
`512..`. Here `N = 33` (target length) and `M = 40` (flag length).

## 3. The transform

```
t[i] = SBOX[ ((in[i] + i*K1) ^ roll) & 0xFF ],   roll = t[i-1],  roll_0 = K2
```

Everything is invertible -- there is no one-way function. `SBOX` is a bijection (the
256 distinct data bytes at offset 0), so it has an inverse `SBOX_inv`.

## 4. Invert -> recover the phrase

For each `i`, let `u = SBOX_inv[target[i]]`. Then, because `roll` is a byte,
`u = ((in[i] + i*K1) ^ roll) & 0xFF = ((in[i] + i*K1) & 0xFF) ^ roll`, so:

```
in[i] = ((u ^ roll) - i*K1) & 0xFF        # then set roll = target[i]
```

Walk `i = 0..N-1`:

```python
sbox_inv = [0]*256
for x, y in enumerate(SBOX): sbox_inv[y] = x
roll, phrase = K2, []
for i, t in enumerate(target):
    u = sbox_inv[t]
    phrase.append(((u ^ roll) - i*K1) & 0xFF)
    roll = t
# phrase == b"the_nam_shub_of_enki_severs_babel"
```

(If you don't want to pull `N` off the disassembly, brute the target/flag_ct split:
for each candidate `N`, invert and test whether `flag_ct ^ phrase` starts with
`flag{` -- exactly what `solve.py` does.)

## 5. Speak it

Feed the recovered phrase back to the VM; loop 2 decrypts and prints the flag:

```
$ printf 'the_nam_shub_of_enki_severs_babel' | ./enkivm asherah.nam
flag{sp34k_th3_nam_shub_and_babel_falls}
```

## Why the obvious shortcuts fail

- **`strings` / grep:** the flag is stored as `flag_ct = flag XOR phrase`, never
  plaintext. The phrase is never stored at all.
- **"Just XOR the two data blobs":** `target ^ flag_ct` is garbage. The compare uses
  `target` (the *transformed image* of the input), but the flag's keystream is the
  *input itself* (the pre-image). You cannot decrypt without inverting the transform
  to get the actual input.
- **Patch out the `CMP`:** skipping the gate lets loop 2 run with a wrong input, so
  it decrypts with the wrong keystream -> garbage, not a flag. The key *is* the input.
- **Brute force the input:** the phrase is 33 bytes; the search space is hopeless.
  Inverting the transform is the path of least resistance (which is the point).

There is exactly one gate, one decrypt, one output path, and no second reader of the
flag data -- no unintended solve.

---

## GM: build / verify / deploy

```
make            # compile+strip enkivm, assemble asherah.nam, write SHA256SUMS
make verify     # rebuild, then run the official solver end-to-end (must pass)
make clean
```

`asherah.nam` is deterministic (fixed RNG seed in `build.py`), so a clean rebuild
is byte-identical. **Deploy:** static file challenge -- no service, no network.
Attach the three `dist/` files in CTFd (`state: hidden` until release).

## GM: re-roll before the event

Edit `src/build.py` (`PHRASE`, `FLAG`, `K1`, `K2`, optionally the S-box seed),
then `make` + `make verify`, and set `flags:` in `challenge.yml` to the new
`FLAG`. **Also update the Answer block at the top of this file** -- it hard-codes
the phrase/flag/constants and will otherwise drift from the build (this already
bit an earlier roll).
