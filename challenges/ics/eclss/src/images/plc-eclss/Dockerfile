# ECLSS ship PLC: OpenPLC v4.3.1 with the ECLSS program compiled in and running
# at start. Modbus TCP on 502; the runtime API only on 127.0.0.1:8443.
# Build context: src/   (docker compose build, or tools/challenge_images.py)
FROM ghcr.io/autonomy-logic/openplc-runtime:v4.3.1

# Same data directory at build time and at run time (the runtime only picks
# /var/run/runtime by itself when it detects a container).
ENV OPENPLC_PERSISTENT_DATA_DIR=/var/run/runtime

COPY images/plc/bake.sh /tmp/bake.sh
COPY build/program.zip /tmp/program.zip
RUN sed -i 's/\r$//' /tmp/bake.sh \
 && bash /tmp/bake.sh /tmp/program.zip 502 8443 \
 && rm -f /tmp/bake.sh

EXPOSE 502
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -kfsS https://127.0.0.1:8443/api/version > /dev/null || exit 1
