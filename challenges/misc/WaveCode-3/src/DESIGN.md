# WaveCode 3 — GM design

The Certus Quartz crystal replaces the printed recovery cards from the earlier
draft. The story is unchanged: RPC WAYFARER is out of power and the crew needs
the reactor restart authorization.

The authorization is written into the crystal's spatial lattice at the factory
and read destructively; the hull logger captures the last read. The mod
references are flavor only — certus quartz, fluix doping, skystone, meteor
provenance, charger, inscriber, spatial lattice — and none of them are needed to
solve. Keep them out of machine-consumed fields (filenames, frequencies,
headers), where they would just be noise.

Three captures, one electrode bank each. A pilot tone identifies the bank because
the filenames deliberately do not. Each ring-down carries one 25-symbol frame:
the nine-symbol header `WC2:0010:` plus sixteen payload symbols. Three frames of
sixteen payload symbols give the 48-symbol envelope: length, up to 42 message
bytes, zero padding, and a five-digit CRC-32.

There is no Reed-Solomon layer. Error correction existed for phone photographs;
this capture is deterministic, with no noise, offset, or clipping. A correct
decay correction recovers bytes exactly, the fixed header validates every frame,
and the CRC rejects a bad reading. The intended decode is a least-squares fit
against the published decaying carriers. A simple peak measurement with a
partial-window correction is close but leaks between neighbouring resonators, so
it is not sufficient on its own; the header exposes that mistake immediately.

The resonators are constant-Q: `tau_i = Q / (pi * f_i)` with `Q = 300` over
`8 + 4i` Hz for `i = 0..24`. The 16-bit logger runs at 48 kHz with a fixed gain
of `0.04`; quantization is far below one symbol step. Each capture is 1.9
seconds: pilot, drive sweep, and a 1.5 second ring-down starting at 0.400 s. The
drive sweep is above the data band and is not part of any frame.

`encoding.md` is the trimmed revision 2 transport specification. Part 2 on
`main` still ships the older, more explicit copy; a follow-up PR makes the two
identical. Do not bundle that change here.

See `solution/solution.md` for the intended solve and the verification steps.
