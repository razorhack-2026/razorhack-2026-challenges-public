# Wear Your Sunscreen

**Author:** Lt. Niko Copernicus
**Category:** Cryptography
**Difficulty:** HARD

## Description

The error logs are encrypted?? This is not good at all. It looks like the encryption keys stored on the telescope server were corrupted by radiation, so we have no way to decrypt the logs. \*Sigh\* I've gotta run to a meeting, could you please try to recover the keys and decrypt the logs?

## Files Provided

- `errorLogs.zip` - A zip file containing the encrypted error logs.

## Flag

`flag{s0l4r_fl4r3}`

## Solution

1. The player is given a zip file containing encrypted error logs and is told that the encryption keys stored on the telescope server were corrupted by radiation.
2. The player researches zip cracking tools and finds `bkcrack`, a tool that can recover the keys used to encrypt a zip file if the player has access to some known plaintext.
3. The player uses the observation metadata from the site in `challenges/cryptography/Ticket-1024` to find a copy of the observation file also stored in the zip file on [MAST](https://mast.stsci.edu/search/ui/#/hst).
4. The player uses `bkcrack` to recover the encryption keys using the known plaintext and the encrypted zip file.
5. The player uses the recovered keys to decrypt the error logs and finds the flag.

## Solve Script

See `solution/solution.sh` for a script that automates the solution process.
Usage: `solution/solution.sh <path_to_folder_with_bkcrack_executable>`

## Hints

- 50pts: Hubble Space Telescope data is publicly available. Find an archive of HST data.
- 100pts: Check MAST's HST archive.

## Notes

- See `src/build.sh` for a script that builds the challenge zip file.
- TODO: The zip file must be rebuilt just before CTF start because MAST periodically updates observation data preventing bkcrack from working.
- If the solve script fails, rebuild the zip file to get the latest observation data and try again.

## Techniques / Tags

`bkcrack`, `zip`, `known-plaintext`
