# Power-Trip bench rig image.
#
# Stage 1 cross-compiles the RPC-IC220 firmware; stage 2 runs it under Unicorn
# behind a socat UART bridge. Build context is the challenge root:
#   docker build -f deploy/Dockerfile -t power-trip .
#
# .dockerignore keeps solution/ and dist/ out of the context -- the image must
# never contain the reference solver or the sealed blob.

FROM debian:stable-slim AS firmware

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc-arm-none-eabi make \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY src/firmware/ ./
RUN make && test -s target.bin


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends socat \
 && rm -rf /var/lib/apt/lists/*

COPY deploy/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /opt/rig
COPY --from=firmware /build/target.bin /opt/rig/firmware/target.bin
COPY src/rig.py           /opt/rig/rig.py
COPY src/device_key.txt   /opt/rig/device_key.txt
COPY deploy/entrypoint.sh /opt/rig/entrypoint.sh
RUN chmod +x /opt/rig/entrypoint.sh

RUN useradd -r -u 10001 rig
USER rig

ENV PORT=1337
EXPOSE 1337

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD printf 'ID\r\nQUIT\r\n' | socat - TCP:127.0.0.1:${PORT} | grep -q RPC-IC220

ENTRYPOINT ["/opt/rig/entrypoint.sh"]
