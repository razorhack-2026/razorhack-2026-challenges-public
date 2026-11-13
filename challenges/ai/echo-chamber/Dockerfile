# Echo Chamber oracle — CPU inference. The flag is injected at RUNTIME
# (-e FLAG=...); it is never baked into an image layer.
FROM python:3.11-slim

ENV HOME=/tmp PYTHONUNBUFFERED=1

# CPU-only torch is all the oracle needs at runtime. (Without numpy, torch logs a
# harmless "Failed to initialize NumPy" warning to stderr — inference is unaffected;
# append `numpy` to this line if you want clean server logs.)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

WORKDIR /app
# challenge code + the EXACT weights that ship in dist/ (harness/dump parity)
COPY src/train.py src/plant.py src/serve.py ./
COPY dist/model.pt ./dist/model.pt

# drop privileges (defense in depth)
RUN useradd -r -u 10001 ctf && chown -R ctf:ctf /app
USER ctf

EXPOSE 9100
CMD ["python", "serve.py", "--model", "dist/model.pt", "--host", "0.0.0.0", "--port", "9100"]
