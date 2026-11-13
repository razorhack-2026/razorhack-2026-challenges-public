# RazerPowerCo Override Record Image Format

Each PNG stores one override record: an unsigned record index and an unsigned
record value. The image is an RGB byte container; its visible colors have no
additional meaning.

## Byte layout

All offsets below refer to the unscaled image's RGB byte stream, not to offsets
in the compressed PNG file. Integers are unsigned and use big-endian byte order.

| Byte offset | Length | Field | Representation |
| --- | --- | --- | --- |
| 0 | 6 bytes | Format marker | ASCII `OVRDKY` (hexadecimal `4F 56 52 44 4B 59`) |
| 6 | 32 bytes | Record index | Unsigned big-endian integer, zero-padded on the left |
| 38 | 10 bytes | Reserved | All zero bytes |
| 48 | L bytes | Record value | Unsigned big-endian integer, zero-padded on the left |
| 48 + L | P bytes | Row padding | All zero bytes |

The value length is determined by the field modulus `p`:

`L = ceil(bit_length(p) / 8)`

The current encoder uses a 256-bit modulus, so `L = 32`. The modulus itself is
not stored in this image format.

The padding length is:

`P = (48 - ((48 + L) mod 48)) mod 48`

Padding is added only when required to complete a row. It is not part of the
record value. Parse the value using its fixed length rather than stripping
trailing zero bytes, which may belong to the value itself.

## Logical pixel layout

The logical image has 16 columns. Each pixel contains three 8-bit channels in
red, green, blue order, so each row stores 48 bytes.

Bytes are assigned to pixels from left to right, then top to bottom. Each
consecutive three-byte group supplies one pixel's red, green, and blue channels.
There are no separators between fields; a field may begin or end within a pixel.

The 48-byte header fills the first logical row. The record value and row padding
occupy the remaining rows. The logical height is `(48 + L + P) / 48`.

With the current 32-byte value, the logical image is 16 pixels wide and 2 pixels
high. The second row contains the 32-byte value followed by 16 zero padding bytes.

## PNG representation

The encoder enlarges the logical RGB image by an integer factor of 32 along both
axes using nearest-neighbor scaling. Each logical pixel becomes a solid 32 by 32
block with exactly the same RGB values. No interpolation or color blending is
applied.

The current output dimensions are therefore 512 pixels wide and 64 pixels high.
There are no borders, labels, or extra image rows.

When interpreting the file, use decoded RGB channel values from the original
PNG. One sample from each 32 by 32 block represents one logical pixel. The byte
stream is the logical pixels in row order, with channels ordered red, green,
blue. PNG compression does not alter those values; screenshots and conversions
to lossy formats are not equivalent representations.

Files are named `share_<index>.png`, where `<index>` is the decimal record index.
The index is also stored in the header.

## Format limitations

The record contains no checksum, authentication tag, modulus, or reconstruction
threshold. A valid marker, dimensions, and padding identify a structurally valid
record; they do not authenticate its contents.
