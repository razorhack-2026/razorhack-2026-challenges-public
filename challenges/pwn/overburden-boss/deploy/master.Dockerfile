# Board B — Extraction Master (BLACK BOX). Never published, never handed out.
# Build context = the challenge dir (see deploy/docker-compose.yml).
FROM python:3.11-slim
RUN useradd -m -u 10002 master
WORKDIR /app
COPY src/master.py /app/master.py
USER master
# FLAG + PORT come from compose. Binds 127.0.0.1 in the namespace it shares with
# the gateway (compose network_mode: service:master) -> reachable only via the gateway.
CMD ["python", "/app/master.py"]
