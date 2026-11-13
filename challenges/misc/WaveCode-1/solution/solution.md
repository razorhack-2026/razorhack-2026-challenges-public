# WaveCode 1 — GM notes

This is the introductory frequency-analysis challenge in the planned WaveCode
series. Only part 1 is implemented here. It is intentionally Easy: locating the
strongest spectral peak is the entire task. Automated tools can solve it quickly;
there is no anti-tool or obfuscation layer.

## Build and solve

Python 3 standard library only; no installation or live service is needed.
From the challenge directory:

```sh
python3 src/main.py
python3 solution/solution.py
```

The solver also accepts an explicit CSV path. It reads only that competitor
artifact, never the generator or metadata. Compare its output with the static
flag in `challenge.yml`. Publish only `dist/beacon.csv` and the public prompt.

## Intended solution

1. Read the `timeSeconds` and `amplitude` columns. Derive the sample rate as
   the reciprocal of the spacing between timestamps.
2. Compute an FFT and inspect magnitudes at positive frequencies, ignoring DC.
3. Find the largest magnitude bin and convert its index to hertz with
   `frequency = bin_index * sample_rate / sample_count`.
4. Round to an integer and apply the submission format from the prompt.

The recording contains 16,384 samples at 8,192 Hz (two seconds), giving 0.5 Hz
bin spacing. All three stationary sine components land exactly on FFT bins;
no windowing is needed. Their amplitudes are distinct, their summed amplitude
is below one, and all frequencies are below Nyquist. The phases vary
but do not encode data. Values are rounded to twelve decimal places. The reference
solver uses an iterative radix-2 FFT without third-party dependencies.

## Review

Confirm the CSV contains only timestamps and total amplitudes, that only the
CSV is listed for download, and that the public prompt and metadata description
match. Rebuilding is deterministic. Parts 2 and 3 live in
`challenges/misc/WaveCode-2` and `challenges/misc/WaveCode-3`.
