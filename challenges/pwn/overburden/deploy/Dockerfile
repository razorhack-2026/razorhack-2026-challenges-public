# Overburden — build the vulnerable RTU, serve it fork-per-connection via socat.
# Build from the challenge dir:  docker build -f deploy/Dockerfile -t overburden .
FROM debian:stable-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY src/rtu_server.c src/Makefile ./
RUN make && ./rtu_server </dev/null; true   # smoke: links & runs

FROM debian:stable-slim
RUN apt-get update && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 rtu && mkdir -p /app && chown rtu:rtu /app
WORKDIR /app
COPY --from=build /src/rtu_server /app/rtu_server
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh /app/rtu_server
USER rtu
EXPOSE 9000
# Secrets via env ONLY (never baked in):  FLAG=flag{...}   (see deploy/README.md)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  sh -c 'printf "RP\020\000\000" | socat - TCP:127.0.0.1:9000,connect-timeout=3 2>/dev/null | grep -q RazerPowerCo' || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]
