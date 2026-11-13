# Consensus-Drift instance image: anvil (from the foundry image) + a small Python
# deploy/dispenser layer. Build context is the challenge root:
#   docker build -f deploy/Dockerfile -t consensus-drift .
FROM ghcr.io/foundry-rs/foundry:latest

USER root
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# isolated venv for the deploy/dispenser tooling
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY deploy/requirements.txt /app/requirements.txt
RUN /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r /app/requirements.txt

# runtime code + PUBLIC params only (never genesis.json / solution / node DBs).
# The contract ships precompiled (ConvoyBridge.json) so no solc is needed in-container.
COPY src/ConvoyBridge.json   /app/ConvoyBridge.json
COPY src/deploy_params.json  /app/deploy_params.json
COPY src/deploy.py           /app/deploy.py
COPY deploy/dispenser.py    /app/dispenser.py
COPY deploy/entrypoint.sh   /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# solcx caches solc under HOME; keep it readable for the non-root user
ENV HOME=/root
WORKDIR /app
EXPOSE 8545 9000
ENTRYPOINT ["/app/entrypoint.sh"]
