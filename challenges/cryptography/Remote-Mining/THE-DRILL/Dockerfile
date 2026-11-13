# THE-DRILL: SSH server hosting the three Drill Containment Units.
# Build context is the challenge folder (see ../docker-compose.yml). The units are
# whatever crypto*.py files are in src/: Termite-01 (crypto.py) ships with Remote
# Mining; Dog-02 and Mole-03 add crypto_level2.py / crypto_level3.py there.
# .dockerignore keeps solution/ and the dev files out of the build.
FROM debian:bookworm-slim

# Retries help on slow or flaky networks.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends openssh-server python3 procps tzdata \
    && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_* /etc/update-motd.d/*

# Challenge code is owned by 'drill' and unreadable to everyone else.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin drill \
    && groupadd teams \
    && install -d -o drill -g drill -m 700 /opt/dcu /var/lib/dcu
COPY src/ THE-DRILL/dcu_daemon.py /opt/dcu/

COPY THE-DRILL/dcu /usr/local/bin/dcu
COPY THE-DRILL/dcu-login.sh /etc/profile.d/dcu-login.sh
COPY THE-DRILL/motd /etc/motd
COPY THE-DRILL/sshd_config /etc/ssh/sshd_config.d/drill.conf
COPY THE-DRILL/teams.txt /etc/dcu/teams.txt
COPY THE-DRILL/entrypoint.sh /entrypoint.sh

# Permissions are set here rather than with COPY --chmod, which needs BuildKit.
RUN chown -R drill:drill /opt/dcu && chmod 700 /opt/dcu && chmod 600 /opt/dcu/* \
    && chmod 755 /usr/local/bin/dcu /entrypoint.sh \
    && chmod 644 /etc/profile.d/dcu-login.sh /etc/motd /etc/ssh/sshd_config.d/drill.conf \
    && chmod 600 /etc/dcu/teams.txt

# Host keys made at build time, so every copy started from this image (one per team, a fresh
# one at each Start) has the same SSH identity and players don't hit "REMOTE HOST
# IDENTIFICATION HAS CHANGED". The compose files mount THE-DRILL/host_keys over this
# directory, where entrypoint.sh creates and keeps its own, as before.
RUN install -d -m 755 /etc/ssh/host_keys \
    && for type in ed25519 ecdsa rsa; do ssh-keygen -q -t "$type" -N '' -f "/etc/ssh/host_keys/ssh_host_${type}_key"; done

EXPOSE 22
CMD ["/entrypoint.sh"]
