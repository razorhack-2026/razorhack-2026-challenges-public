# Course Correction — Solution

## Extract the shares

Each PNG in `dist/shares/` is a 16-column RGB record enlarged by a factor of 32
using nearest-neighbor scaling. Sample one pixel from each 32×32 block and flatten
the logical pixels in row order, with channels ordered RGB.

Check the first six bytes are `OVRDKY`. Read bytes 6–37 as the unsigned big-endian
share index and bytes 48–79 as the unsigned big-endian share value. Ignore the
reserved bytes and trailing padding. See `dist/encoding.md` for the full format.

## Correct the modified shares

There are 63 shares of a polynomial of degree at most 30. The threshold is
31, allowing correction of 16 unknown modified values because
`63 = 31 + 2 × 16`.

Perform all arithmetic modulo:

```text
0x8c0cbcbc4f4769ccc6e6f767f426ff71febf667c07aa311582d768f2a5b9ea97
```

For the extracted pairs `(x_i, y_i)`, calculate:

\[
w_i=\left(\prod_{\ell\ne i}(x_i-x_\ell)\right)^{-1},
\qquad
S_j=\sum_i w_i y_i x_i^j,\quad j=0,\ldots,31.
\]

Run Berlekamp–Massey on these 32 syndromes to obtain the shortest recurrence
polynomial `C(z)`, with constant coefficient one and the convention:

\[
S_j+C_1S_{j-1}+\cdots+C_LS_{j-L}=0.
\]

A share is modified when `C(x_i⁻¹) = 0`. Discard those shares, then interpolate
using any 31 remaining shares. Recover the constant term with:

\[
s=f(0)=\sum_{i\in G}y_i
\prod_{\substack{\ell\in G\\\ell\ne i}}
\frac{-x_\ell}{x_i-x_\ell}\pmod p.
\]

Division means multiplication by a modular inverse. Verify that the interpolated
polynomial matches every share except the identified modified shares.

## Use the recovered key

Render `s` as lowercase hexadecimal without a `0x` prefix. Enter that text into
`dist/navigation_console.py`. Use the same text as the password to open
`dist/navigation_log.zip` with an AES ZIP-compatible tool such as 7-Zip, then read
`navigation_log.txt`.

Submit the hexadecimal key wrapped as `flag{<override_key>}`.

## Reference solver

From the repository root, run:

```bash
python3 challenges/cryptography/course-correction/solution/solution.py
```

The solver reads `dist/shares/`, identifies the modified shares, and prints the
recovered hexadecimal override key. It requires NumPy and Pillow.
