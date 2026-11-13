# Extended Authority

**Category:** Cryptography
**Difficulty:** Medium
**Author:** Lt. Rico Kopernicus

## Description

Central Command swears its fleet directives can't be faked - every order carries a
"Directive Authentication v1" checksum, and they use a shared signing secret.
It's a fixed byte string held only by Centcom and its fleet.
We believe this isn't enough.
See if you can submit a forged directive that successfully authenticates.

```
checksum = SHA256(secret || directive)
```

## Flag

`flag{f0rg3d_th3_0rd3r}`

This challenge quietly canonizes how the Icarus was emptied (a forged RPC_CENTCOM directive with a "valid
header, malformed origin block"), but the story premise is carried entirely on the
gateway's own homepage. The gateway never mentions *what* order to forge; any forged
directive that carries its own order works, so it gives away none of the abandon-ship
easter-egg lore from Lt. Rico's DB challenges.

## The vulnerability

`checksum = SHA256(secret || message)` is a **secret-prefix MAC** over a Merkle-Damgard hash.
It is vulnerable to a **length-extension attack** (this is exactly why real systems use
HMAC, which is *not* vulnerable). SHA-256 processes input in 64-byte blocks and its
final internal state *is* the digest. So given a valid `(message, checksum)` pair you can:

1. Load SHA-256's internal state from the known `checksum` (the 64 hex chars).
2. Recreate the **glue padding** SHA-256 appended to `secret || message` (a `0x80`, zero
   bytes, then the 64-bit big-endian bit length). This depends on `len(secret)`, which
   you don't know - so you brute-force it.
3. Resume hashing from that state over your own appended bytes, producing a valid checksum for
   `secret || message || glue || append` - **without ever knowing the secret**.

The forged message contains the raw glue-padding bytes in the middle - that junk is the
canon "malformed origin block." The gateway authenticates raw bytes, so it doesn't care.

The gateway returns the flag whenever it authenticates a directive that is **not** the
untouched reference sample **and** that carries its own `order=...` field in the appended
block - i.e. an actionable forgery. A forgery that appends only junk with no `order=`
authenticates but is treated as inert and gets no flag, so the append must splice in an
order. (The genuine order sits before the glue padding and doesn't count - only an
`order=` in the attacker-controlled tail after the glue does.)

## Solution

1. Grab the genuine captured pair from the gateway homepage - the "Last received directive"
   panel shows the directive (hex-encoded) and its checksum. The directive is a fixed
   byte string, so only the per-deploy checksum needs reading off the page:
   ```bash
   curl -s http://<host>:8888/ | grep -oE '"checksum": *"[0-9a-f]{64}"'
   # "checksum": "<64 hex>"
   ```

2. Run the length-extension forgery. The signing secret's length is unknown, so loop over
   candidate lengths and, for each, extend the hash. Conceptually (using `hashpumpy`, if it
   builds on your Python):
   ```python
   import re, hashpumpy, requests
   base = "http://<host>:8888"
   # Directive is constant; only the checksum is per-deploy, so hard-code the directive
   # and scrape just the checksum with a plain regex.
   directive = bytes.fromhex(
       "5250435f43454e54434f4d7c763d317c68756c6c3d4943415255537c7072693d"
       "726f7574696e657c6f726465723d44454c495645525f5041594c4f4144")
   html = requests.get(base + "/").text
   checksum = re.search(r'"checksum": *"([0-9a-f]{64})"', html).group(1)
   for klen in range(0, 65):
       forged_checksum, forged_msg = hashpumpy.hashpump(checksum, directive,
                                                    b"|origin=RPC_CENTCOM|order=ABANDON_SHIP", klen)
       r = requests.post(base + "/verify",
                         data={"directive_hex": forged_msg.hex(), "checksum": forged_checksum})
       if "flag{" in r.text:
           print(klen, r.text); break
       time.sleep(0.6)   # gateway is throttled to 2 req/s
   ```
   `hashpumpy.hashpump(orig_checksum, orig_data, data_to_add, key_len)` returns
   `(new_checksum_hex, new_message_bytes)`; the new message already includes the glue padding.
   The run with the correct key length returns `DIRECTIVE AUTHENTICATED`, an `order:` line
   echoing the `order=...` field from your appended block (here `ABANDON_SHIP` - the canon
   forged abandon-ship order), and the flag. The append **must** carry an `order=`;
   append-only junk with no order authenticates but is inert and yields no flag. The
   shipped `solution.py` does the same with a built-in pure-Python SHA-256 so it
   needs no external package (see note below).

   The reference solver is `solution.py`. It ships a **pure-Python** SHA-256
   length extension (no third-party dependency - the `hashpumpy` C binding fails to build /
   import on modern CPython), scrapes the homepage for the pair, brute-forces the secret length, and backs off
   on the rate-limit 429s. Runs on any modern Python:
   ```bash
   python3 solution.py http://<host>:8888
   # ...
   # [+] secret length = XX
   # [+] directive_hex = ...
   # [+] checksum = ...
   # [+] flag{f0rg3d_th3_0rd3r}
   ```

### Alternative tooling: `hash_extender`

Per candidate key length (loop the `--secret` value):
```bash
hash_extender --data 'RPC_CENTCOM|v=1|hull=ICARUS|pri=routine|order=DELIVER_PAYLOAD' \
  --secret <klen> --append '|origin=RPC_CENTCOM|order=ABANDON_SHIP' \
  --signature <checksum> --format sha256 --out-data-format hex
# submit the printed new signature + hex data to POST /verify
```

## Known Issues / Notes

- **Per-deploy secret.** The signing secret's value *and* length are randomized in-memory
  at container start and never exposed, so a value/length from another team won't work -
  the length must be recovered by brute force each deploy. The solver is deploy-agnostic
  (it reads the live sample).

## Techniques / Tags

`cryptography`, `length-extension`, `sha256`, `mac-forgery`, `web`
