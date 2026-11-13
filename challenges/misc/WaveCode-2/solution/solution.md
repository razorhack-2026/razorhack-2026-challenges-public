# WaveCode 2 — GM writeup

## Build and solve

Python 3 standard library only. From the challenge directory:

```sh
python3 src/main.py
python3 solution/solution.py
```

The solver accepts an optional CSV path. It reads only that download and uses
the rules in `dist/encoding.md`; it does not read source plaintext or metadata.
It prints the recovered distress packet, including the secret AUTH field.
Do not paste its output into public logs or a PR description.

## Intended solution

1. Load timestamps and amplitudes from the CSV. Derive sample rate from spacing.
2. Compute the full capture's FFT. There is no windowing requirement because
   every carrier lands on a bin.
3. Read slots at 8, 12, 16, ... Hz. Convert each positive-frequency magnitude to
   amplitude with `2*abs(X[k])/N`, then multiply by 128 and round to ASCII.
4. Decode the first nine symbols and parse the four hexadecimal length digits.
5. Decode that many additional symbols. Submit the packet's AUTH value.

The reference script implements an iterative radix-2 FFT without dependencies.
A successful review must recover the complete source packet byte for byte and
match AUTH exactly against `challenge.yml`. Publish only the CSV and encoding
specification.

## Story continuation

The packet points to a ship on emergency power with life support about to fail.
The crew needs help reading a printed reactor-restart authorization card after
its optical reader was destroyed. WaveCode 3 will supply that physical waveform
and finder patterns; it is a separate challenge, not an extra step for this flag.
