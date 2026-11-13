# Adversarial Memory replay oracle -- disposable, isolated, unprivileged.
# Build + run from the challenge dir:  bash deploy/run.sh
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir numpy cryptography \
    && useradd -m -u 10001 relay
WORKDIR /app
COPY service/replay.py service/embedder.py /app/
COPY dist/corpus.jsonl dist/queries.jsonl /app/data/
ENV DATA_DIR=/app/data
USER relay
EXPOSE 9443
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python -c "import socket,ssl;ssl._create_unverified_context().wrap_socket(socket.create_connection(('127.0.0.1',9443),3)).close()" || exit 1
# Runtime env only (never baked in): FLAG (required); KB_KEY optional.
CMD ["python", "/app/replay.py"]
