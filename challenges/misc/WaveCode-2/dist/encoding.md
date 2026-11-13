# WaveCode — legacy beacon transport, revision 2

## Samples

`beacon.csv` contains `timeSeconds` and `amplitude`. Time is measured in seconds;
amplitude is in arbitrary linear units. Rows are uniformly spaced, starting at
zero. The capture contains one complete frame.

## Symbol mapping

The frame is 7-bit ASCII. For zero-based symbol position `i`:

- `f_i = 8 + 4*i` hertz
- `A_i = ASCII(symbol_i) / 128`

The transmitted waveform is:

`signal(t) = sum(A_i * sin(2*pi*f_i*t))`

## Frame layout

The first nine ASCII symbols are `WC2:LLLL:`, where `LLLL` is a four-digit,
uppercase hexadecimal count of payload bytes. The header uses the same frequency
slots and amplitude mapping as the payload.
