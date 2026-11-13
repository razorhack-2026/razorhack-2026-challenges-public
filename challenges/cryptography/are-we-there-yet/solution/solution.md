# Are We There Yet?

**Category:** Cryptography  
**Difficulty:** Medium  
**Author:** Lt. Niko Copernicus

## Description
Navigation has reported that the ship is beginning to drift from the expected course. The navigation system takes in a new flight plan each day and loads the instructions into memory. We keep backups of each day's flight plan in an encrypted archive in case something goes wrong, but the encryption key is split into multiple shares to prevent a single point of failure. There are 9 total shares but only 5 are required to reconstruct the key. 5 shares are physically located around the ship and the other 4 are distributed in other ship systems and materials.

The modulus for each share is `0xa105db01c4ca6f21c129479c720f425a4b20ec314b326ee6080079cbadcb4b71`.

**DISCLAIMER:**

All physical challenge elements are located in publicly accessible competition areas and can be found without damaging, disassembling, moving, or tampering with venue property.

Do **not**:

* Enter staff-only, locked, restricted, or otherwise off-limits areas.
* Open cabinets, ceiling tiles, wall panels, electrical boxes, equipment, or furniture.
* Move heavy furniture or venue equipment.
* Unplug, disconnect, dismantle, or modify anything.
* Climb on furniture, fixtures, railings, or other structures.
* Remove NFC tags or other challenge props from where they are placed.

If finding a challenge item would require any of the above, **it is not there**.

When in doubt, ask a Game Master before interacting with something.

## Files Provided

No files provided. Shares will be distributed among other challenges and around the venue.

## Flag

```flag{sharing_is_caring}```

## Solution

The provided data describes a polynomial over the finite field modulo `p`:

```text
f(x) = a_0 + a_1*x + ... + a_(t-1)*x^(t-1) mod p
```

Each share is a point `(x_i, f(x_i))`. With at least `t` distinct shares, recover the constant
term `a_0 = f(0)` using Lagrange interpolation:

```text
f(0) = sum(y_i * product((-x_j) / (x_i - x_j))) mod p
```

All division is performed in the finite field, so each denominator is replaced by its modular
inverse modulo `p`. The instance has a threshold of five, so any five distinct valid shares are
enough.

After interpolation, convert the recovered integer to a big-endian byte string. Decoding those
bytes as text yields the flag.

## Solve Script

See `solution.py`

## Techniques / Tags

`cryptography`

## Setup / Deployment Notes

The shares will be hidden in various other challenges and around the physical premises.

- x = 1
- x = 2 -> Lt. Rico Kopernicus
- x = 3
- x = 4 -> Flyer
- x = 5 -> Website
- x = 6
- x = 7
- x = 8
- x = 9 -> Davie Bowman

The source script is deterministic but will not match the values in shares.txt. Use shares.txt as the source of truth.

## Printed share cards

`src/print/` holds the printable NFC cards and tag payloads. By default print `share-01.pdf`, `share-03.pdf`, `share-06.pdf`, `share-07.pdf`, and `share-08.pdf` — the five shares with no other listed location. Write each tag from `nfc_payloads.txt` and mount it behind the dashed circle on the card. `src/print/README.md` has the full print, tag-writing, and placement procedure. Shares x = 2/4/5/9 are the crew/material handouts and do not get wall cards.

