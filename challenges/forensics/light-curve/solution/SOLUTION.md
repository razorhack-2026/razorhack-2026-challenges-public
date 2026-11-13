# Light Curve — Solution (GM-only)

Verified 2026-09-22 by running `generate.py` → `light_curve.csv` → `solution.py`
end-to-end from `dist/`.

**Flag:** `flag{th3_r34l_s1gn4l_1s_1n_th3_n01s3}`

## Concept

`light_curve.csv` is a historian-style telemetry export with columns `timestamp, tag,
raw_value, scaled_value, quality`. `raw_value` is a simulated 16-bit ADC/Modbus-style
register; `scaled_value` is just `raw_value / 50000`, rounded — a linear rescale, nothing
more.

`scaled_value` plotted on its own looks like a real periodic exoplanet transit light
curve (genuine dips, photometric noise) — a deliberate, convincing dead end. The flag is
hidden in the least-significant bit of `raw_value`, one bit per row, framed by:

- a 16-bit sync word `0xA5A5` (alternating-bit pattern, the classic sync-word shape)
- an 8-bit length prefix (payload length in bytes)
- the payload itself, MSB-first ASCII, one bit per row

## Solve path

1. Plot `scaled_value` — recognize it as a real-looking but non-encoding transit curve.
   It's the intended dead end.
2. Notice `raw_value` and `scaled_value` are just a linear rescale of each other —
   `scaled_value` alone is redundant unless `raw_value` carries something extra.
3. Extract `raw_value & 1` for every row as a bitstream.
4. Read the first 16 bits as a 16-bit big-endian integer — recognize `0xA5A5` as a
   framing/sync-word header.
5. Read the next 8 bits as a length prefix (in bytes).
6. Read `8 * length` bits as MSB-first ASCII → flag. Reference implementation:

```python
bits = [int(row["raw_value"]) & 1 for row in rows]
sync = bits_to_int(bits[0:16])          # 0xA5A5
length = bits_to_int(bits[16:24])       # payload length in bytes
payload = bits[24:24 + 8*length]        # MSB-first ASCII
```

7. Everything past the payload (the last 260 rows) is tail noise with no hidden bits —
   not part of the frame, just padding so the file doesn't end exactly at the payload
   boundary (which would itself be a tell).

## Notes

- `generate.py`'s `SEED` is fixed (`20260824`), so the decoy transit curve and noise are
  reproducible — regenerating with the same seed produces byte-identical output.
- Difficulty is entirely in recognizing that `raw_value` carries more than `scaled_value`
  does, then recognizing the sync-word framing — there's no cryptography here, just LSB
  steganography over a legitimate-looking telemetry format.
