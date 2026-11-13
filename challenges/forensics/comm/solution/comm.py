import struct, wave
with wave.open("dist/static_loop.wav", "rb") as w:
    frames = w.readframes(w.getnframes())
samples = struct.unpack(f"<{len(frames)//2}h", frames)
bits = [samples[i] & 1 for i in range(0, len(samples), 7)]
data = bytearray()
for i in range(0, len(bits) - 7, 8):
    data.append(sum(bits[i + j] << j for j in range(8)))
open("recovered.png", "wb").write(data)