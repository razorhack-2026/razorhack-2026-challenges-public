#!/usr/bin/env python3
"""
Light Curve challenge generator.

Produces a historian-style CSV of photometer telemetry (timestamp, tag,
raw_value, scaled_value, quality). The scaled_value column is a decoy: a
realistic periodic-transit light curve with photometric noise, meant to look
like the whole point of the file. The flag is actually hidden in the
least-significant bit of each raw_value register (a simulated 16-bit ADC
reading), framed by a 16-bit sync word (0xA5A5) and an 8-bit length prefix.

Regenerate with a new SEED to get a fresh (but still valid) light curve.
"""
import csv
import random
from datetime import datetime, timedelta

FLAG = "flag{th3_r34l_s1gn4l_1s_1n_th3_n01s3}"
SYNC_WORD = 0xA5A5           # 16-bit frame sync, MSB first
CADENCE_S = 120              # seconds between samples
ADC_SCALE = 50000            # nominal ADC counts at flux = 1.0
NOISE_SIGMA = 120            # photometric noise, in ADC counts
TRANSIT_PERIOD_SAMPLES = 620
TRANSIT_DURATION_SAMPLES = 14
TRANSIT_DEPTH = 0.016
TAIL_SAMPLES = 260           # extra real samples after the message; LSBs are natural, not part of the frame
SEED = 20260824


def bits_of(flag):
    bits = []
    bits += [(SYNC_WORD >> i) & 1 for i in range(15, -1, -1)]
    length = len(flag)
    if length > 255:
        raise ValueError("flag too long for an 8-bit length prefix")
    bits += [(length >> i) & 1 for i in range(7, -1, -1)]
    for ch in flag:
        code = ord(ch)
        if code > 255:
            raise ValueError("flag must be ASCII/Latin-1 (8 bits/char)")
        bits += [(code >> i) & 1 for i in range(7, -1, -1)]
    return bits


def true_flux(sample_idx, rng):
    phase = sample_idx % TRANSIT_PERIOD_SAMPLES
    in_transit = phase < TRANSIT_DURATION_SAMPLES
    dip = TRANSIT_DEPTH if in_transit else 0.0
    flux = 1.0 - dip
    flux += rng.gauss(0, NOISE_SIGMA / ADC_SCALE)
    return flux


def main():
    rng = random.Random(SEED)
    bits = bits_of(FLAG)
    total_samples = len(bits) + TAIL_SAMPLES
    start = datetime(2178, 3, 12, 22, 0, 0)

    rows = []
    for i in range(total_samples):
        flux = true_flux(i, rng)
        raw = round(flux * ADC_SCALE)
        raw = max(0, min(65535, raw))
        if i < len(bits):
            raw = (raw & ~1) | bits[i]
        scaled = round(raw / ADC_SCALE, 6)
        ts = (start + timedelta(seconds=CADENCE_S * i)).isoformat() + "Z"
        rows.append([ts, "PHOT.CCD1.FLUX", raw, scaled, "GOOD"])

    with open("light_curve.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "tag", "raw_value", "scaled_value", "quality"])
        w.writerows(rows)

    print(f"Wrote light_curve.csv with {total_samples} samples.")
    print(f"Embedded flag: {FLAG}")
    print(f"Frame: {len(bits)} bits (16 sync + 8 length + {8 * len(FLAG)} payload), "
          f"plus {TAIL_SAMPLES} tail samples with no hidden bits.")


if __name__ == "__main__":
    main()
