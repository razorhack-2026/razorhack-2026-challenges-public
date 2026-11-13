import re, struct, wave
from pathlib import Path
def solve():
    from rapidocr_onnxruntime import RapidOCR
    artifact=Path(__file__).parents[1]/"dist/static_loop.wav"
    with wave.open(str(artifact),"rb") as w:
        frames=w.readframes(w.getnframes())
    samples=struct.unpack(f"<{len(frames)//2}h",frames)
    bits=[samples[i]&1 for i in range(0,len(samples),7)]
    data=bytes(sum(bits[i+j]<<j for j in range(8)) for i in range(0,len(bits)-7,8))
    image_path=Path(__import__("tempfile").gettempdir())/"microbot-comm-recovered.png"
    image_path.write_bytes(data)
    result,_=RapidOCR()(str(image_path))
    text=" ".join(item[1] for item in (result or []))
    match=re.search(r"flag\{[^}]+\}",text,re.I)
    if not match: raise ValueError("offline OCR could not read token")
    return match.group(0)
