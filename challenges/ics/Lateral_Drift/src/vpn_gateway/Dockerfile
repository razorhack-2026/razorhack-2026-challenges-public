FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        curl \
        iputils-ping \
        net-tools \
        nano \
    && rm -rf /var/lib/apt/lists/*

# rootkit / the VPN credential recovered in Know Your Mark - foothold only, no sudo.
# This is a disposable, single-purpose jump box scoped to this challenge's own network
# segment (mirrors challenges/pwn/Blind_Spot's attacker pattern).
RUN useradd -m -s /bin/bash rootkit \
    && echo "rootkit:icarus_override" | chpasswd \
    && mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# The second credential, left behind as a world-readable ops backup - an unencrypted
# tarball in a world-readable path, not a bash-history scrollback (reads like a real
# ops mistake, gives a concrete artifact to extract/grep rather than scroll through).
COPY eng-sync.conf /tmp/eng-sync.conf
RUN mkdir -p /opt/backups \
    && tar -czf /opt/backups/eng-sync.tar.gz -C /tmp eng-sync.conf \
    && rm /tmp/eng-sync.conf \
    && chmod 644 /opt/backups/eng-sync.tar.gz \
    && chmod 755 /opt/backups

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
