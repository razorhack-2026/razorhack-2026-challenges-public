# Ticket #1024

**Category:** Cryptography
**Difficulty:** Medium
**Author:** Lt. Niko Copernicus

## Description (what the competitor will see)

The on-board telescope is acting up again??? They only call when something breaks! I guess I could pull another all-nighter... actually, could you take this over for me? I have way too much on my plate. I have no idea what went wrong, but you can connect to the telescope's [control panel](http://localhost:8000) and go through the error logs. The only problem is I forgot the credentials for the admin account... but I'm sure you're smart enough to figure it out.<!--TODO: add actual url-->

## Files Provided

- N/A

## Flag

`flag{ecb_not_for_me}`

## Solution

1. Player connects to control panel and sees forms to request access.
2. Player receives access cookie. They are then presented with visuals one would expect to see in a viewing session.
3. Player views page cookies and sees that the `session` cookie is a base16-encoded string with `.` characters delimiting groups of 16, hinting at the block-based encryption.
4. Player requests access with a different crew ID. They then view the page cookies again and see that the `session` cookie has changed, but is still a base16-encoded string with `.` characters delimiting groups of 16.
5. Player looks into block-based encryption and realizes that the `session` cookie is likely encrypted using DES in ECB mode, which is vulnerable to a cut-and-paste attack.
6. Player tests where the block boundary after the crew ID ends is by creating accounts with increasing lengths of any character (e.g., `a`, `aa`, `aaa`, etc.) and observing the resulting `session` cookie. When the second block stops changing, they have found the block boundary. They find that the block boundary is after 2 characters of the crew ID.
7. Player creates a new account starting with 2 random characters and then appends the string `&role=admin     ` to the end of the crew ID. They will have to guess the format of the session string but it is a standard format they will see on tutorial sites. The extra spaces are for padding to the block size. They then log in and view the `session` cookie, which now has the `&role=admin` string in it in 2 blocks.
8. Player removes the remaining blocks from the `session` cookie after the `&role=admin` string, allowing them to log in as the admin user and view the flag. The correct `session` cookie will be `41c80772a821a1bf.1de386aad9beb3bc.31b6b7b132031ac6.99f355f0b23adb80`.

## Solve Script

- See `solution/solution.py` for a script that automates the above steps and retrieves the flag.

## Hints

- Free: The server uses spaces to pad the crew ID to the block size of the encryption algorithm.

## Notes

- The password for the zip file is `N15c@D$YT8ASpc@7%0`
- TODO: The zip file must be rebuilt just before CTF start because MAST periodically updates observation data preventing bkcrack from working. The current observation data used was downloaded 8-3-2026 and is there for testing only
- Zip build command: `zip -0 -e errorLogs.zip observation.fits error.log` in `src/static`

## Techniques / Tags

`ecb`