# Recalculating... Make a U-Turn — Solution

**Category:** Cryptography  
**Difficulty:** Medium  
**Author:** Lt. Niko Copernicus

## Intended Solution

The flight plan uses polynomial evaluation over the finite field GF(257), with erasures.

1. Split each artifact line into twelve three-character symbols. Hexadecimal values are field
   elements; `???` marks a missing symbol. Keep the original symbol positions.
2. Interpret positions 1 through 12 as evaluation coordinates. Each row evaluates a polynomial
   of degree at most seven modulo 257. The eight coefficients, in ascending degree order, are
   the character values of an eight-character plaintext block.
3. At most four symbols are erased per row, leaving at least eight distinct evaluations.
   Use Lagrange interpolation modulo 257 to recover the coefficients. Extra
   surviving evaluations can be used to check the result.
4. Convert the coefficients to bytes, concatenate the blocks in order, and remove trailing
   null padding. The reconstructed flight plan contains the flag.

Competitors receive only the data file. Recognizing the fixed-width symbols and erasures,
inferring the field and polynomial representation, and recognizing readable reconstructed
text are part of the analysis. The reference solver supplies those inferred parameters;
it does not read the generator, plaintext source, or metadata.

## Solve Script

- Run `python solution.py` from within the `solution` directory.

## Known Issues / Notes

- This format handles marked erasures, not arbitrary symbol errors. Do not introduce unmarked
  corruption without changing the design and reference solver.
