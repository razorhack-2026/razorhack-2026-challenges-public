#!/usr/bin/env python3
"""COMM artifact generator. Writes dist/static_loop.wav.

src/image.png is hidden, bit by bit, in the least significant bit of every 7th
sample ("channel 7") of an otherwise unremarkable static loop. Players extract
those bits, write them back to a file, and open the reconstructed PNG. The flag
is painted on the image; it is not in the audio as text.

Deliberately stdlib-only: no numpy or Pillow needed to generate or to solve.
"""
import os
import random
import struct
import wave

IMAGE_NAME = "image.png"
# Painted on the source image. challenge.yml must use this exact value.
FLAG = "flag{comm_d1str3ss_ackn0wl3dg3d}"

SAMPLE_RATE = 44100
STRIDE = 7  # embed in every Nth sample
NOISE_SEED = 20260823  # fixed so the artifact is reproducible
PAD_SECONDS = 1  # trailing static after the payload so the file is not flush


def bits_of(payload: bytes):
    """Yield bits LSB-first within each byte."""
    for byte in payload:
        for i in range(8):
            yield (byte >> i) & 1


def main():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(src_dir, IMAGE_NAME)
    if not os.path.isfile(image_path):
        raise SystemExit(f"missing cover payload: {image_path}")

    payload = open(image_path, "rb").read()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{IMAGE_NAME} is not a PNG (bad magic)")

    out_dir = os.path.join(src_dir, "..", "dist")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "static_loop.wav")

    bits = list(bits_of(payload))
    needed_samples = (len(bits) - 1) * STRIDE + 1
    total_samples = needed_samples + SAMPLE_RATE * PAD_SECONDS

    rng = random.Random(NOISE_SEED)
    # Keep amplitude well inside int16 range so flipping a bit never overflows.
    samples = [rng.randint(-12000, 12000) for _ in range(total_samples)]

    for bit_index, sample_index in enumerate(range(0, total_samples, STRIDE)):
        if bit_index >= len(bits):
            break
        samples[sample_index] = (samples[sample_index] & ~1) | bits[bit_index]

    frames = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames)

    duration = total_samples / SAMPLE_RATE
    size = os.path.getsize(out_path)
    print(f"wrote dist/static_loop.wav ({size:,} bytes, {duration:.1f}s)")
    print(f"embedded {IMAGE_NAME} ({len(payload):,} bytes) across {len(bits):,} carriers")
    print(f"flag (painted on the reconstructed image): {FLAG}")


if __name__ == "__main__":
    main()
