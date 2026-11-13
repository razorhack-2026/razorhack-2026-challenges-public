# Singularity Upset

- **Category:** Misc
- **Difficulty:** Easy
- **Author:** Lt. Niko Copernicus

## Description

Communications just detected a distress signal coming from a nearby black hole. The data from this signal is stored in `msg.txt`. The only problem is that the radiation and relativistic effects of the black hole have corrupted the data. Can you help us recover the original message?

## Files Provided

- `msg.txt` - The corrupted message data

## Solution

1. Player sees human-readable metadata in `msg.txt` and comes to the conclusion that Hamming (7, 4) was likely used
2. Player uses Hamming algorithm to reconstruct the message, retrieving the flag

## Solve Script

- See `solution.py`
