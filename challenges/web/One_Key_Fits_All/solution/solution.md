# One Key Fits All — Solution

## Real-world grounding

- **The fiction.** OT at RazerPowerCo wasn't actually touched by the
  ransomware, but operations were shut down as a precaution anyway. This
  mirrors the real **Colonial Pipeline incident (May 2021)**: the ransomware
  hit Colonial's IT/business network, not the pipeline's OT/control
  systems, but Colonial proactively shut the pipeline down because they
  couldn't be confident the two were cleanly separated, and because
  billing/logistics systems the pipeline depended on were down anyway. We
  reuse that exact precautionary-shutdown pattern here.

- **Vulnerability #1 — IDOR on the gang's own portal.** Real ransomware
  crews increasingly run victim-facing "customer support" portals so
  victims can check negotiation/payment status (this is now common enough
  that security researchers routinely catalog these leak/support sites).
  An IDOR (Insecure Direct Object Reference) — an object/record reachable
  by guessing or walking its id, with no ownership check — is consistently
  one of the most common web vulnerabilities found in the wild (it's been
  a fixture of the OWASP Top 10 broken-access-control category for years).
  `src/portal/app.py`'s `/victim/<id>` route is exactly that: no session,
  no auth, no check that the requester's case id is the one being
  requested.

- **Vulnerability #2 — the shared static key.** Cheap/low-effort
  ransomware-as-a-service kits have repeatedly shipped with a single
  hardcoded encryption key reused across every victim instead of generating
  one per deployment — this is a real, documented weakness class, and it's
  the entire reason **nomoreransom.org** (the joint law-enforcement/industry
  initiative) can offer free decryptors for several ransomware families:
  researchers recovered the strain's one static (or otherwise
  under-protected) key once, and it works for every victim of that strain
  forever after. `src/box/build_locked_file.py` encrypts the flag payload
  with a key that is deliberately the *same* value the portal hands back
  to the one paid victim — VoidCrypt's kit, in-fiction, never actually
  generates a unique key per deployment.

This is intentionally **not** a cryptography challenge — the symmetric
cipher (Fernet, which is authenticated AES-128-CBC + HMAC under the hood)
is never attacked. The two real bugs are access control (IDOR) and key
management (one key, reused everywhere).

## Build layout

- `src/portal/app.py` — Flask portal with sparse case IDs. An HTML comment on the home page names an archived-notice path. That page links to payment-status information and then a customer directory. The directory lists 750 opaque customer IDs; exactly one corresponding profile is settled and identifies the associated support case. The case endpoint lacks an ownership check and returns the recovery key for that case.
- `src/box/` — the Dockerfile for the affected RazerPowerCo machine: real
  `sshd`, a normal user (`rpc_tech`, password handed directly in
  `challenge.yml`/README), and two files pre-placed in that user's home
  directory: `locked_dashboard.bin` (the encrypted payload) and
  `voidcrypt_recover` (the gang's own decryptor CLI, in-fiction tooling
  found on the compromised host).
- `src/box/build_locked_file.py` — GM-only. Encrypts the real flag payload
  with VoidCrypt's static key (Fernet) to produce `locked_dashboard.bin`,
  which is the only artifact that ends up inside the box image. The
  plaintext payload never ships anywhere; it lives only as a Python string
  inside this script, which stays in `src/`.
- `src/box/voidcrypt_recover` — the decryptor CLI itself
  (`./voidcrypt_recover --key <key> locked_dashboard.bin`): a banner, a
  short animated "validating/decrypting" sequence, a taunting failure
  message on a wrong/missing key (no partial decrypt, no flag), and on the
  correct key a live ANSI dashboard-reveal animation (status rows flipping
  from red `ALARM`/`LOCKED` to green `NOMINAL`/`ONLINE` across a few
  frames) ending with the flag in a highlighted box, all rendered directly
  in the competitor's SSH session.
- `docker-compose.yml` — `portal` (published `8080`) and `box` (published
  `2222` → container `22`), independent services, no special network
  capabilities. `box` shares `portal`'s network namespace, as in the per-team
  Fargate task, where players reach sshd on `22` (ports can't be remapped).
- `dist/` — intentionally empty; nothing to download, everything is live.

## Solve path

1. Inspect the support portal's HTML source and find the archived-notice path in a comment.
2. Follow the notice page's payment-status link, then download the customer directory.
3. Check the customer profiles programmatically. One profile is settled and identifies its support case.
4. Visit that case's `/victim/<id>` page; its missing ownership check exposes the recovery key.
5. SSH into the affected machine with the provided credentials and use the installed recovery tool with the key.
6. The key is reused, so the encrypted dashboard is recovered and displays the flag.

`solution/find_customer_case.py` handles the portal/customer-record stage and prints the case reference plus recovery key. `solution/recover_dashboard.py` connects to the test box and runs the supplied recovery program. `solution/solve.py` remains the combined reference solver. Run the containers with `docker compose up --build -d`, then use the connection arguments in each script's usage text. Stop the stack with `docker compose down`. Verification (2026-11-04, `solve.py` against the live compose stack): recovered the exact flag configured in `challenge.yml`. The paid customer's organization name is built from the same word lists as every other customer, so it can't be spotted in the CSV by name. Competitor-facing leak check (`README.md`, `dist/`) clean.

## Design note: the recovery tool

The recovery tool only exposes the payload after successful decryption. The deliberate design choice worth flagging for a reviewer: `voidcrypt_recover`'s flag line is
extracted from the decrypted payload's last non-blank line rather than
hardcoded in the script itself, so the tool only ever "knows" the flag
after a genuine successful decryption — there is no shortcut that reveals
it without going through the key check.
