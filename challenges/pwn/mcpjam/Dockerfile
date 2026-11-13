# MCPJam Inspector v1.4.2 (vulnerable maintenance build) + MCPJam Console.
#
# Two services, two unprivileged users, one container:
#   - appuser (:6274, public) : the inspector backend. `/api/mcp/connect` is the
#     unauth RCE (CVE-2026-23744); everything else proxies to the console.
#   - console (:6280, loopback): the console front-end, served from a git commit
#     selected by the operator working checkout but sourced from a pristine,
#     console-owned mirror (see devops-cd.sh).
#
# `curl` is present on purpose: the intended stage-1 exploit needs an outbound
# tool available to the code it spawns. `git` drives devops-cd.
FROM node:20-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser \
    && useradd -m -u 10002 console

WORKDIR /mcp
# Inspector backend (public front door + /api/mcp/connect).
COPY src/package.json /mcp/package.json
COPY src/server.js /mcp/server.js

# Console service artifacts.
COPY src/console.bundle /opt/console.bundle
COPY src/devops-cd.sh /opt/devops-cd.sh
COPY src/start.sh /start.sh
RUN mkdir -p /opt/console \
    && chown console:console /opt/devops-cd.sh \
    # root:root, owner-only — PID 1/root is the only thing that ever execs
    # this, and devops-cd.sh is only ever exec'd as `console`; both were
    # previously 0755 and readable by the foothold user (appuser), which
    # leaked the whole stage-2 trust model straight off disk via the RCE.
    && chmod 0500 /start.sh /opt/devops-cd.sh \
    # operator working checkout — writable by the foothold user so they can
    # `git checkout` a different commit (the "revert"):
    && git clone -q -b main /opt/console.bundle /opt/console/staging \
    # pristine mirror — owned by console, the only source we actually serve:
    && git clone -q --bare -b main /opt/console.bundle /opt/console/.release.git \
    && rm -f /opt/console.bundle \
    && chown -R appuser:appuser /opt/console/staging \
    && chown -R console:console /opt/console/.release.git \
    # defense in depth: git's own pack-file modes are world-readable
    # regardless of chown, so strip "other" bits explicitly.
    && chmod -R o-rwx /opt/console/.release.git \
    && mkdir -p /opt/console/prod && chown console:console /opt/console/prod \
    # deploy trigger: a FIFO, not a regular file — appuser (falls under
    # "other") can write to request a deploy, but can't read from it, and
    # there's no content to inject since devops-cd only checks that *something*
    # was written, never what.
    && mkfifo -m 0622 /opt/console/deploy.trigger \
    && chown console:console /opt/console/deploy.trigger

ENV NODE_ENV=production
EXPOSE 6274

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:6274/health || exit 1

# Runs as root only long enough to write the flag files, then drops privileges.
ENTRYPOINT ["/start.sh"]
