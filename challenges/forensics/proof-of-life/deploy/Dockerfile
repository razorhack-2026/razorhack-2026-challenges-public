# Proof of Life relay -- disposable, isolated, unprivileged.
# Build + run from the challenge dir:  bash deploy/run.sh  (docker compose, flag from challenge.yml)
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir cryptography \
    && useradd -m -u 10001 relay
WORKDIR /app
COPY src/relay.py /app/relay.py
USER relay
EXPOSE 9443
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python -c "import socket,ssl;ssl._create_unverified_context().wrap_socket(socket.create_connection(('127.0.0.1',9443),3)).close()" || exit 1
# Runtime env only (never baked in): FLAG (required); SIGNING_SECRET (optional, random per start).
# IMPLANT_CRED / MISSION_SECRET / CONFIG_KEY default to the chain's canon values in relay.py.
CMD ["python", "/app/relay.py"]
