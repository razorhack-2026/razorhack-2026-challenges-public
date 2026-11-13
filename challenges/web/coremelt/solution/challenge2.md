# Coremelt: Keys to the Kingdom — reference solution (GM only)

**Scores:** the engineer memo flag, recovered by cracking + decrypting.
**Part 2 of 4.** Requires the RCE foothold from Part 1.

## Deploy

Shared stack — deploy from `challenges/web/coremelt/` (`./build.sh`).
Same live instance for all four parts.

## Solve

With RCE on the CoreWatch container (from Part 1), two artifacts are in the web
root, and **both need a cracked credential — the shell alone yields neither**:

1. `/app/corewatch.db` (SQLite), table `users(username, password_md5, role)`.
   Three rows; **exactly one** cracks against rockyou — `j.reyes` (role
   `engineer`), `md5("supernova1")` (rockyou line 84072). `admin` and
   `svc_monitor` carry random 32-hex digests that never crack.
2. `/app/corewatch.db`, table `rtu_secrets(label, blob)`. The `blob` is base64
   whose head is `U2FsdGVk` — i.e. an `openssl enc` **`Salted__`** container. It
   is the engineer's "RTU maintenance override memo" encrypted with the *same*
   reused password.

Crack the hash, then decrypt the memo — the flag is inside it:

```
# blob = base64 of `openssl enc -aes-256-cbc -pbkdf2` output
echo "<blob>" | base64 -d | \
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 -md sha256 -pass pass:supernova1
```

Lesson: credential reuse — the same password locks the memo here and (Part 3)
logs into the OT workstation.

## Verify with the reference solver

```
cd solution && python3 solve.py <host> 3000
```

This challenge's flag is the one logged at stage `[2]` ("decrypted engineer
memo"). The plaintext memo never ships in the image — only the ciphertext — so
the crack is genuinely required.
