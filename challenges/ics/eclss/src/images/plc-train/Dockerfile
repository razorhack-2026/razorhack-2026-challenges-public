# Training Bay PLC: OpenPLC v4.3.1 with the training program compiled in and
# running at start. Modbus TCP on 5020 (it shares a network namespace with the
# ECLSS PLC on 502); the runtime API only on 127.0.0.1:8444.
# Build context: src/   (docker compose build, or tools/challenge_images.py)
FROM ghcr.io/autonomy-logic/openplc-runtime:v4.3.1

# Same data directory at build time and at run time (the runtime only picks
# /var/run/runtime by itself when it detects a container).
ENV OPENPLC_PERSISTENT_DATA_DIR=/var/run/runtime

COPY images/plc/bake.sh /tmp/bake.sh
COPY build/training/program.zip /tmp/program.zip
RUN sed -i 's/\r$//' /tmp/bake.sh \
 && bash /tmp/bake.sh /tmp/program.zip 5020 8444 \
 && rm -f /tmp/bake.sh

EXPOSE 5020
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -kfsS https://127.0.0.1:8444/api/version > /dev/null || exit 1
