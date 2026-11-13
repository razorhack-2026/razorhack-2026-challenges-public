# WaveCode 2 — GM design

The author selected amplitude encoding with frequency giving character order,
and approved a distress packet leading into the crystal ring-down finale.

Each ASCII character has amplitude equal to its byte value divided by 128.
Slots start at 8 Hz and increase by 4 Hz. Phase is zero. A nine-character
`WC2:LLLL:` header supplies the hexadecimal payload length. The public encoding
specification defines the protocol and the waveform only; it does not describe
how to measure the amplitudes.

The packet identifies RPC WAYFARER, provides fictional rendezvous coordinates,
and explains its failed computer, emergency power, and critical life-support
batteries. Its AUTH field is the part 2 submission. The reactor restart code
lives in a Certus Quartz crystal whose reader was destroyed. This sets up
WaveCode 3 without implementing its encoding or creating its artifacts here.

The CSV has 4,096 samples at 4,096 Hz (one second). Frequency slots align to
integer DFT bins. There is no noise, normalization, or clipping. Scripts use
Python's standard library, execute top to bottom, use single quotes and
camelCase names. Source plaintext and secrets stay GM-only.
