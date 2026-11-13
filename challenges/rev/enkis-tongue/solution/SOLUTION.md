# Enki's Tongue -- Solution

**Answer (this reference build):**
- nam-shub / phrase: `the_true_tongue_of_enki_before_babel`
- flag: `flag{z3_unb1nds_the_true_t0ngue_0f_enki}`

Official solver: `solution/solve.py` (Z3; recovers both from `enki.nam` alone,
proves uniqueness, then confirms through the real `enkivm`). Run `make verify`.

---

## 0. Recon

`enkivm` (small ELF) + `enki.nam` (688 bytes). Wrong input prints nothing;
`strings` shows no `flag{`, but shows `unknown rune 0x%02x` -- an interpreter.

## 1. Reverse `enkivm`

Same shape as the Glossolalia machine: 8x 32-bit regs, a 4 KB tape, 4-byte
instructions `[op][a][b][imm]`, `MIX Ra = tape[Ra & 0xFF]` (S-box at `tape[0..255]`).
**One new op:** `ROL Ra, imm` (0x1A) = 32-bit rotate-left. `.nam` = header
(`magic,code_len,data_len`) then code then data (loaded at `tape[0]`).

## 2. Disassemble `enki.nam` -- three phases

- **Read:** loop `IN` -> `tape[512 + i]` for `n` bytes (the whole input is
  captured *before* any check).
- **Gate:** for each `i`: `state = SBOX[(state + in[i]) & 0xFF]`; `state ^=
  in[jtab[i]]`; compare to `target[i]`. Data layout: `SBOX@0`, `target@256`,
  `jtab@256+n`, `flag_ct@256+2n`.
- **Cipher:** for each `j`: an ARX keystream byte XORed onto `flag_ct[j]`.

`n` falls out of the data: the `jtab` region is `n` bytes all `< n` forming an
arithmetic progression mod `n` (it's `(A*i+B) % n`). `K0` is the `LOADI` into the
register `MIX` uses; `KEY0` is the `LOADI` into the register rotated by 5.

## 3. The gate has no per-byte inverse

Because the gate forces `state == target[i]` at every step, the state entering
step `i` is a *known constant* `C_i` (`K0`, else `target[i-1]`). Each equation is:

```
SBOX[(C_i + in[i]) & 0xFF] ^ in[jtab[i]] == target[i]
```

So `in[i]` is determined by `in[jtab[i]]` -- but `jtab[i]` can be a *later* index,
so you can't go left to right. Two clean ways to solve:

**(a) Z3.** Model each equation over byte variables (S-box as a constrained
`Array`); solve. `solution unique: True`. This is what `solve.py` does:

```python
sb = z3.Array('sbox', z3.BitVecSort(8), z3.BitVecSort(8))
for x in range(256): s.add(sb[x] == sbox[x])
for i in range(n):
    C = K0 if i == 0 else target[i-1]
    s.add((z3.Select(sb, C + inp[i]) ^ inp[jtab[i]]) == target[i])
```

**(b) Cycles.** `jtab` is a permutation, so `i -> jtab[i]` decomposes into cycles.
Guess one byte per cycle, propagate `in[i] = (SBOX_inv[target[i] ^ in[jtab[i]]] -
C_i) & 0xFF` around the cycle, keep the guess that closes it. `O(256 n)`, no Z3.

Either way you recover `the_true_tongue_of_enki_before_babel`.

## 4. Stage 2 -- the flag is a keyed stream cipher

Recovering the phrase is not the flag. During the gate, a key is folded from the
*whole* input:

```
key = KEY0
for i: key = rotl32(key, 5) ^ (in[i] + i)
```

Then a Speck-like ARX keystream (counter mode over `j`) decrypts:

```
def ks(key, j):
    s = rotl32((key ^ j) & M, 7); s = (s + key) & M
    s = (s ^ rotl32(s, 11)) & M;  s = (s + rotl32(key, 3)) & M
    return s & 0xFF
flag[j] = flag_ct[j] ^ ks(key, j)
```

Re-derive `key` from the recovered phrase, run `ks`, XOR `flag_ct` -> flag. Or
just `printf '<phrase>' | ./enkivm enki.nam` and let the VM decrypt.

## Why the shortcuts fail

- **`strings`/grep:** flag is stored XOR-keystream, never plaintext; the phrase is
  never stored.
- **Per-byte inversion:** impossible -- each check needs a scattered, possibly
  future byte (`in[jtab[i]]`).
- **`target ^ flag_ct`:** meaningless -- the flag's keystream is keyed by the
  *whole input*, not by `target`. You must recover the entire phrase and run the
  cipher.
- **Patch out the compare:** the cipher still needs the right key (folded from the
  input), so a wrong input decrypts to garbage.

One gate, one key, one cipher, one output path; the solution is unique (Z3-proven).

---

## GM: build / verify / deploy

```
make                                   # compile+strip enkivm, assemble enki.nam, checksums
make verify PY=/path/venv/bin/python   # Z3 solver end-to-end (needs z3-solver)
make clean
```

`enki.nam` is deterministic (fixed `SEED`), so a clean rebuild is byte-identical.
**Deploy:** static file challenge — no service, no network. Attach the three
`dist/` files in CTFd (`state: hidden` until release); the flag is revealed only
by solving.

## GM: re-roll before the event

Edit `src/build.py` (`PHRASE`, `FLAG`, `SEED`), then `make` + `make verify`, and
set `flags:` in `challenge.yml` to the new `FLAG`. Each `SEED` gives a fresh
S-box + gate/cipher constants; the official solver is generic and recovers
everything from the file. **Also update the Answer block at the top of this file**
— it hard-codes the phrase/flag and will otherwise drift from the build.

## GM: note on hardness

The gate is genuinely cross-byte (no per-byte inverse). Because each byte depends
on exactly one scattered other byte, a sharp solver can skip Z3 and propagate the
`jtab` permutation's cycles — a fair, real reversing path, not an unintended
shortcut. To force Z3 strictly, a future revision can couple each byte with *two*
scattered bytes (the insane-tier knob).
