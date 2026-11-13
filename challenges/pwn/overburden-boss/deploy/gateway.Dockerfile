# Board A — Extraction Gateway (the published, exploitable surface).
# Build context = the challenge dir (see deploy/docker-compose.yml).
FROM debian:stable-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY src/rtu_server.c src/Makefile ./
RUN make

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
# B_HOST / B_PORT come from compose (Board B's internal address). No flag here.
ENTRYPOINT ["/app/entrypoint.sh"]
