# Pinned build environment for the RazorHack ICS challenges.
#
# The OpenPLC v4 runtime only accepts STruC++-generated C++, so building a
# program.zip needs Node + STruC++. This image pins STruC++ to the version
# the OpenPLC Editor ships for runtime v4.3.1, so organizers need nothing
# but Docker:
#
#     docker compose run --rm builder               # main + training
#
FROM node:22-bookworm-slim

ARG STRUCPP_REF=v0.7.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends git python3 ca-certificates g++ \
 && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${STRUCPP_REF}" \
        https://github.com/Autonomy-Logic/strucpp.git /opt/strucpp \
 && cd /opt/strucpp && npm ci && npm run build \
 && npm prune --omit=dev

ENV STRUCPP_DIR=/opt/strucpp
WORKDIR /work
COPY build.sh /usr/local/bin/build.sh
RUN sed -i 's/\r$//' /usr/local/bin/build.sh && chmod +x /usr/local/bin/build.sh
ENTRYPOINT ["/usr/local/bin/build.sh"]
