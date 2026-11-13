# WaveCode 3

**Author:** Lt. Niko Copernicus
**Category:** Misc
**Difficulty:** HARD

## Description

Okay, this is bad. The beacon led us to RPC WAYFARER and she's running on fumes — life support is on its last few hours and her main computer is toast. The reactor restart authorization was never on paper; RazerPowerCo grew it into a Certus Quartz crystal, and the energy acceptor that used to charge it got fried when the reactor scrammed. The hull-strain logger caught the crystal's last interrogation before everything went dark, so those recordings are all we've got. Thing is, a certus-quartz resonator doesn't ring forever, and nobody aboard knows how to read one. I've gotta go help hand-crank the O2 scrubbers — can you get the authorization out of the recordings before the batteries give out?

## Files Provided

- `0e4b0ee53f0640ce.wav` - Logger capture from one of the crystal's three banks.
- `10516b7a7ff9b204.wav` - Logger capture from another bank.
- `d71b1d23309a0b2e.wav` - Logger capture from the last bank.
- `crystal-format.md` - The Certus Quartz crystal and logger capture format.
- `encoding.md` - The WaveCode transport specification used in Part 2.

## Flag

`flag{please_sine_here_to_keep_breathing}`

## Solution

1. The player is given three WAV captures from a Certus Quartz crystal and a format document. Nothing says which file belongs to which bank.
2. The player measures the pilot tone at the start of each capture (130, 150, or 170 Hz) and labels the files A, B, and C.
3. The player reads the ring-down model: 25 resonators at `f_i = 8 + 4*i` Hz, symbol amplitudes `symbol_i / 128`, each decaying as `exp(-t / tau_i)` with `tau_i = Q / (pi * f_i)` and `Q = 300`.
4. The player slices each capture starting at the first ring-down sample (`t = 0`) and recovers the 25 starting amplitudes. A plain full-window DFT underestimates each resonator by a different amount, and a peak correction alone still leaks between neighbouring resonators, so the player fits the decaying sum (for example, least squares over sine and cosine pairs).
5. The player rounds each amplitude times 128 to a symbol and checks the nine known header symbols `WC2:0010:`. A correct header confirms the window and the correction.
6. The player joins the three payloads in bank order and validates the length, zero padding, and CRC-32.
7. The recovered message is the flag.

## Solve Script

See `solution/solution.py` for a script that automates the solution process.
Usage: `solution/solution.py [capture.wav ...]`
The script reads only `dist/` and prints the message. Keep its output private.

## Hints

- 50pts: A ringing mode fades. A measurement over the whole ring-down reports its average loudness, not the loudness at the strike.
- 75pts: The nine header symbols are always `WC2:0010:`. You know exactly what those nine notes should be.

## Notes

- The drive sweep is the strike, not the message; only the samples after each burst carry data.
- See `src/main.py` for the builder. It reads `src/packet.txt` and regenerates all three captures.
- `solution/wavecode.py` holds the shared constants and the payload helpers.
- There is no error correction. The capture is deterministic, so the fixed header and the CRC are the only checks needed.
- Rebuild and re-solve after any change to the message, the gain, `Q`, or the timing. The recovered message must match the flag above.
- Install dependencies with `python3 -m pip install -r requirements.txt`, then run `python3 src/main.py` and `python3 solution/solution.py`. Verified on Python 3.11.2 with NumPy 1.24.2; Python 3.9 or newer should work.

## Techniques / Tags

`fft`, `dsp`, `transient-analysis`, `piezoelectric`, `waveforms`
