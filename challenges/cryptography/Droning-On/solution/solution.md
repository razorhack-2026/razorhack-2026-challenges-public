# Droning On

**Category:** Cryptography
**Difficulty:** Hard
**Author:** Lt. Niko Copernicus

## Description (what the competitor will see)

There seems to be an enemy drone cluster blockading a planet that has vital resources. Communications intercepted some of the inter-drone messages, but they're all encrypted and I can't figure out what they're using. Take a crack at it for me.

## Files Provided

- `encrypted.txt` - The intercepted message and the public key of the drone that sent it

## Flag

`flag{choose_e_not_d}`

## Solution

1. Player realizes this is probably also RSA, but now e is much larger than is standard.
2. Player researches large e values and finds that it likely means d is small, allowing Wiener's attack to be used.
3. Player implements Wiener's attack and recovers the private key.
4. Player uses the private key to decrypt the message and recover the flag.

## Notes

d = 0x4a7e11f545856dd6fb7ab6eb43170632f259228c056d3c96d81abcefd0ac8365

## Solve Script

See `solution/solution.py`

## Techniques / Tags

`rsa`
