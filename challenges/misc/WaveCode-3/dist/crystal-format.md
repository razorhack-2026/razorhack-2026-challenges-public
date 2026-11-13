# RazerPowerCo Certus Quartz authorization crystal

The Certus Quartz bank is a piezoelectric authorization crystal grown from a
meteor fragment and seated in a skystone cradle. A reactor controller charges one
electrode bank, listens to it ring down, and reads the authorization from the
loudness each resonator had at the instant of the strike. Readout is destructive:
one strike per bank, and the recording is the only copy.

## Crystal

Each capture comes from one bank of 25 resonators, cut from a single
fluix-doped boule and trimmed to the carrier frequencies in the model below. The
controller's charger sweeps 200 Hz to 2000 Hz to excite the bank. The
authorization was inscribed once at the factory, and the logger only ever reads.

## Recordings

Three logger captures are provided. Their filenames are opaque hexadecimal
identifiers and carry no information. Each is a mono 48 kHz, 16-bit PCM WAV
holding one pilot tone, one drive sweep, and one ring-down from a single bank.

The logger applies a fixed gain of `0.04`. Divide every sample by `32767` and by
`0.04` to recover crystal amplitude units.

The capture is deterministic: no noise, no offset, no drift, no clipping, and one
channel only. The WAV contains standard format fields and nothing else.

## Layout

| Time (s) | Contents |
| --- | --- |
| 0.000 - 0.200 | Bank pilot, amplitude 0.5 |
| 0.200 - 0.230 | silence |
| 0.230 - 0.380 | Drive sweep, 200 Hz to 2000 Hz, amplitude 0.6 |
| 0.380 - 0.400 | silence |
| 0.400 - 1.900 | Ring-down |

The drive sweep is the interrogation, not data.

## Bank pilots

| Pilot (Hz) | Bank |
| ---: | --- |
| 130 | A |
| 150 | B |
| 170 | C |

Frame order is bank A, then bank B, then bank C. Each capture holds one frame.

## Ring-down model

For zero-based resonator `i`, with `i = 0..24`:

- `f_i = 8 + 4*i` hertz
- `A_i = symbol_i / 128`
- `tau_i = Q / (pi * f_i)`, with `Q = 300`
- phase is zero at the first ring-down sample

`signal(t) = sum(A_i * exp(-t / tau_i) * sin(2*pi*f_i*t))`

Time `t` is measured from the first sample of the ring-down. `A_i` is the
amplitude at the instant of the strike. The model is exact. The ring-down lasts
1.5 seconds.

## Frame layout

Each frame is the nine-symbol header `WC2:0010:` followed by sixteen payload
symbols, using the transport rules in `encoding.md`. The header occupies
resonators zero through eight; the payload occupies resonators nine through
twenty-four.

## Payload

Join the three payloads in bank order to obtain 48 symbols:

- Index 0: message length `L`, from 1 through 42.
- Indices 1 through L: the ASCII authorization.
- Indices L+1 through 42: zero padding.
- Indices 43 through 47: the unsigned IEEE CRC-32 of the message bytes only,
  written as five big-endian seven-bit digits: shifts 28, 21, 14, 7, and 0. The
  first digit is at most 15.

Validate the length, the padding, and the checksum before accepting a reading.
