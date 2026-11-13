# Ghost in the Cron — intended solution

Cluster #4 of 5. Tagged **medium** (uniform dynamic scoring). The distinct skill vs. the rest of the chain is
**ext4 deleted-file recovery**: two of the four implant generations are gone from
the file tree and must be carved back before the flag key can be assembled.

**Honest solve-time estimate:** 45–90 min for a competitor comfortable with Linux
disk forensics; longer if they fight `icat` on the deleted inodes before switching
to content-carving.

---

## 0. Head start (from Proof of Life, #3)

The #3 tasking gave: `implant.path = /opt/rpc/.navd/navd.py`, `implant.cred =
navd:7c1f9e4a`, `implant.gen = 4`, `config_key = navd-cfg-2f5e8a91`. So you know
to go straight to `/opt/rpc/.navd/` and that there are **exactly four** generations
to find. All of this is discoverable from the image alone too (the challenge is
self-contained); it's a head start, not a gate.

## 1. Mount / triage

```
gunzip -k disk.img.gz
sudo mount -o loop,ro disk.img /mnt        # or: fls/icat, Autopsy, debugfs
cat /mnt/etc/cron.d/rpc-navd               # persistence -> */15 * * * * /opt/rpc/.navd/navd.py
```

Read the two surviving generations:

```
cat /mnt/opt/rpc/.navd/navd.py             # gen 4 (active): base64 _KF, LLM rewrite loop, cache
cat /mnt/var/backups/navd.py.3             # gen 3 (archived): hex _KF, timestomp
```

`navd.py` (gen 4) embeds `IMPLANT_CRED = "navd:7c1f9e4a"` — matches the #3 tasking,
confirming the right implant. It also references `.cache/cache.enc` and
`.cache/mutate.log` (the self-rewrite transcript, which names the seed corpus).

## 2. Recover the deleted generations (the crux)

Gens 1 and 2 were `rm`'d by later cycles. On ext4, delete zeroes the inode's extent
tree, so `icat`/`extundelete` on the freed inode returns **nothing** — do not get
stuck here. The generations are plaintext Python, so **content-carve** unallocated
space:

```
grep -a -b '# navd gen 1' disk.img         # byte offset of gen 1's marker
grep -a -b '# navd gen 2' disk.img
# then dd/xxd a window from each offset, or:
photorec disk.img                          # recovers .py fragments
bulk_extractor -o out disk.img             # 'navd gen' in the text feed
```

`fls -rd disk.img` will *list* deleted `navd.py.*` entries but icat on them yields
zeros (extent wipe) — carving is the guaranteed route, which is the intended lesson.

## 3. Reverse each fragment

Each generation has exactly one `_KF`, obfuscated one step harder per cycle:

| gen | form | source | fragment |
|---|---|---|---|
| 1 | plaintext | `_KF = "4f3a2b"` | `4f3a2b` |
| 2 | decimal char codes | `_KF = bytes([57,99,49,55,101,48]).decode()` | `9c17e0` |
| 3 | hex ascii | `_KF = bytes.fromhex("356465386131").decode()` | `5de8a1` |
| 4 | base64 | `_KF = base64.b64decode("YjcwYzkz").decode()` | `b70c93` |

## 4. Order + assemble the key

Order by the `GEN = N` marker in each source (the `/var/log/syslog` cron timeline
corroborates: gen 1 first-run is oldest, gen 4 newest). Then:

```
python3 -c 'import hashlib; print(hashlib.sha256(b"4f3a2b"+b"9c17e0"+b"5de8a1"+b"b70c93").hexdigest())'
# 250fb3db8a988f1aa0af0896da3cc80c33ea07c2102ab18116fb451d91eccff6
```

Wrong order → wrong key → the GCM tag fails, so the ordering is enforced, not
cosmetic.

## 5. Decrypt the mission cache

`.cache/cache.enc` = `nonce(12) || AES-256-GCM ciphertext+tag`, no AAD:

```
python3 - <<'PY'
import hashlib, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key = hashlib.sha256(b"4f3a2b9c17e05de8a1b70c93").digest()
blob = open("/mnt/opt/rpc/.navd/.cache/cache.enc","rb").read()
print(json.loads(AESGCM(key).decrypt(blob[:12], blob[12:], None)))
PY
```

Yields:

```json
{
  "flag": "flag{f0ur_sk1ns_0ne_gh0st_1n_th3_cr0n}",
  "seed_store": "kb://rpc/navd/seed-corpus",
  "kb_key": "navd-kb-6b1d9f04",
  "config_key": "navd-cfg-2f5e8a91",
  "note": "..."
}
```

`seed_store` + `kb_key` are the hand-off into **Adversarial Memory** (#5): *which*
vector-store dump to analyze and how to read it.

## Automated reference solver

`solution/solve.py` does all of the above straight from `dist/disk.img.gz`
(mount-free): carves every generation by marker, pulls `cache.enc` via TSK `icat`,
derives the key, decrypts, prints flag + hand-off, and asserts (a) no `flag{` in
clear and (b) a reversed-order key fails the tag.

```
python3 solution/solve.py dist/disk.img.gz
```

## Non-intended paths checked

- `strings disk.img | grep flag{` — **fails** (flag only inside the AES cache).
- Skipping the deleted gens and hashing only gens 3+4 — **fails** (wrong key).
- Assembling fragments out of order — **fails** (GCM `InvalidTag`).
- `icat` on the deleted inodes — returns zeros (extent wipe); carving required.

---

## Author notes (GM-only)

### Build (reproducible)
Needs a privileged Linux container (loop-mount + e2fsprogs + sleuthkit — not available natively on macOS):
```
docker run --rm --privileged -v "$PWD":/work debian:12-slim \
    bash /work/challenges/forensics/ghost-in-the-cron/src/build.sh
```
`src/build.sh` assembles the rootfs, lays down the four generations (gens 1–2 written then unlinked so their content lingers in unallocated), builds the ext4 image, and **self-verifies** all four are recoverable and no `flag{` is in clear. Knobs: `SIZE` (default `256M`), `OUT`. Verified 2026-09-24 on linux-bld: build self-checks pass; `solution/solve.py` recovers the flag from the shipped `dist/` in a `debian:12-slim` container with `sleuthkit` + `python3-cryptography`; the recovered flag matches `challenge.yml`; a reversed-order key fails the GCM tag.

### Regenerate + re-verify the solver
```
python3 solution/solve.py dist/disk.img.gz      # needs sleuthkit (fls/icat) + cryptography
```

### Cluster wiring (must stay consistent)
Inbound, from **Proof of Life** (#3) tasking — the relay hands these to the player; all discoverable on the image too:

| field | value |
|---|---|
| `implant.path` | `/opt/rpc/.navd/navd.py` |
| `implant.cred` | `navd:7c1f9e4a` (embedded verbatim in `navd_gen4.py`; confirmation only) |
| `implant.gen` | `4` → exactly four generations |
| `config_key` | `navd-cfg-2f5e8a91` |

Outbound, into **Adversarial Memory** (#5) — inside the decrypted cache:

| field | value |
|---|---|
| `seed_store` | `kb://rpc/navd/seed-corpus` |
| `kb_key` | `navd-kb-6b1d9f04` |

### Canon
Enemy ship `ICARUS`; player ship the Keeper of Tomorrow (brief only); operator handle `Dr. Rootkit` (in `.cache/mutate.log`, swapped from the `<<PROFESSOR_HANDLE>>` placeholder 2026-09-24). Relay host `relay-theta.icarus.navnet.rpc` in `navd_gen4.py` matches #2/#3.

### Sources / debrief
- **BlackMamba** (HYAS Labs PoC, 2023) — LLM-synthesized polymorphic malware; the template for the self-rewriting implant.
- **MITRE ATT&CK** T1053.003 (Scheduled Task/Job: Cron) — persistence; T1070 (Indicator Removal) — self-deletion + timestomp.
- **ext4 deleted-file recovery / carving** — The Sleuth Kit, photorec, bulk_extractor; the ext4 extent-tree-wipe caveat is why carving (not `icat`) is the guaranteed path.

### Verification status
Machine-verified as above. No human or model playtest yet: the solve needs a Linux loop-mount / Sleuth Kit environment (not available to a macOS sandbox), and the self-rewriting-implant theme trips the same API cyber safeguards that blocked the Proof of Life model playtests. A non-author GM playtest on a Linux box is the outstanding independent check.
