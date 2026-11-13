# Recalculating... Make a U-Turn

**Category:** Cryptography  
**Difficulty:** Medium  
**Author:** Lt. Niko Copernicus

## Description

*Sigh* Just my luck... it looks like the flight plan backup was corrupted. Based on the archive's documentation, flight plan backups are encoded in 8-byte blocks that map to 12-symbol codewords via a Reed-Solomon-style code. Its arithmetic is done over the smallest prime field large enough to represent each symbol. The archive stores enough data to determine which symbols were damaged, but not their original values. Please recover the flight plan quickly, the captain is breathing down my neck!

## Files Provided

- [flight_plan.dat](dist/flight_plan.dat)
