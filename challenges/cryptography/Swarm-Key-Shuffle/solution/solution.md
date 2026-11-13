# Swarm Key Shuffle

**Author:** Lt. Niko Copernicus
**Category:** Cryptography
**Difficulty:** HARD

## Description

The drone cluster went quiet after we cracked that last key. When it came back, it stopped reusing anything. Every handshake hands out a fresh public key and an encrypted clearance token, and the relay drops you if you fumble the token. We're tapped into one of their relay nodes, but the trick you used last time doesn't work anymore. Get the token back before the swarm rotates.

The relay is live. See `protocol.txt` for the commands and key rules.

## Files Provided

- `protocol.txt` - Relay commands, key parameters, session limits, and a non-secret test vector.

## Flag

`flag{shuffle_off_this_mortal_lattice}`

## Solution

1. Connect to the relay and send `KEY`. The relay returns a 1024-bit `N`, a large `e`, an encrypted `C`, and a session id.
2. The relay samples `d` with `0.255 <= log_N(d) <= 0.265` (service-side only; the public protocol does not state the bound). This is the same small-`d` shape as Droning On, but further out.
3. Wiener's attack only reaches `d < N^0.25 / 3`, so continued fractions fail.
4. Use Boneh–Durfee for `d < N^0.292`. Build the Herrmann–May lattice for `f(x, y) = x(N + 1 + y) + 1`, run LLL/BKZ, and take resultants of two short polynomials.
5. A root `y0 = -(p + q)` gives `phi(N) = N + 1 + y0`, so `d = e^-1 mod phi(N)`. Verify with `pow(2, e*d, N) == 2`.
6. Decrypt the token: `pow(C, d, N)` as 16 big-endian bytes.
7. Send `AUTH <session> <token-hex>`. The relay releases the flag.

Each session uses a fresh key and token, so the attack must run against the live values. Validate an implementation on locally generated keys with known parameters before spending a relay session.

## Solve Script

See `solution/solution.py` for a script that automates the solution process.
Usage: `solution/solution.py --host <host> --port <port>`
Install its dependencies with `python3 -m pip install -r solution/requirements.txt` (`fpylll`, `cysignals`, `sympy`). The script reads only the relay protocol and prints the flag. Runtime is roughly 20 seconds per key on a laptop.

## Hints

- 25pts: The key pattern is familiar, but the private exponent must be outside the bounds for Wiener's Attack since it doesn't work.
- 75pts: Boneh-Durfee covers d < N^0.292.

## Notes

- See `src/main.py` for the relay. It generates each session, validates the token, and releases the flag.
- `docker-compose.yml` mounts the GM-only `src/flag.txt` into the container read-only. The flag is never in `dist/`.
- No test vector is published; validate the lattice on keys you generate yourself.
- Session limits: sessions expire after 120 s if never used (1800 s once an AUTH is sent), 5 attempts,
  5 sessions per connection, one `KEY` every 3 s, a global KEY issuance token bucket (50 burst /
  20 per second), and a global concurrent-session cap of 10000.
- Limits are deliberately NAT-safe: nothing is keyed on client IP, so participants sharing the campus
  egress address are unaffected. `MAX_TOTAL_SESSIONS` is a global pool with a short unused-session TTL
  instead of a per-IP cap.
- Rebuild and re-solve after changing the delta band or lattice parameters. The reference solver uses `m = 5`, `t = 2`, and a `delta = 0.27` bound.

## Techniques / Tags

`rsa`, `lattice`, `boneh-durfee`, `lll`, `fpylll`, `live-service`
