# Course Correction

**Category:** Cryptography

**Difficulty:** Hard

**Author:** Lt. Niko Copernicus

## Description

I need your help again! I sent that flight plan backup to navigation and we're on a collision course with the nearest star! Navigation has been trying to override the flight plan but they're reporting that the navigation system is refusing the override key! The override key is distributed between the 63 controllers around the ship but it can be reconstructed from the data on any 31 of them. The controllers are reporting that 16 of the shares have been modified and are no longer valid. We need to find the valid shares and reconstruct the override key so we can get back on course! We will collide with the star in 24 hours so get to it!

The controllers store the shares in a custom graphical format. Engineering has provided the image files for each of the 63 controllers as well as the specification for the format. The specification is in the `encoding.md` file and the image files are in the `shares/` directory. They have also provided the modulus for the shares, which is `0x8c0cbcbc4f4769ccc6e6f767f426ff71febf667c07aa311582d768f2a5b9ea97`. I included a simulation of the navigation console in the `navigation_console.py` file. The simulation will accept the override key and report whether it is valid or not. You can use this to verify that you have reconstructed the correct override key.

Navigation also supplied `navigation_log.zip`, an AES-256 encrypted ZIP archive containing `navigation_log.txt`. Open it with the exact override key text as the password to read the recovery log. Use an AES ZIP-compatible tool such as 7-Zip; the password is the hexadecimal override key without the flag wrapper.

The flag is flag{<override_key>}. The override key is a 16-byte hexadecimal string.

## Files Provided

- `dist.zip` - This archive contains all the following files
- `encoding.md` - The specification for the custom graphical format used to store the shares on the controllers.
- `shares/` - A directory containing the image files for each of the 63 controllers. Each image file contains a share of the override key, but some of them may have been modified and are no longer valid.
- `navigation_console.py` - A simulation of the navigation console that will accept the override key and report whether it is valid or not. You can use this to verify that you have reconstructed the correct override key.
- `navigation_log.zip` - An encrypted navigation recovery log, protected with the override key as its password.
