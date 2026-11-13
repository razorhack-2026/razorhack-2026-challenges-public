FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections \
    && apt-get install -y --no-install-recommends \
        openssh-server \
        iproute2 \
        net-tools \
        tcpdump \
        tshark \
        nano \
        sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir scapy==2.6.1 pymodbus==3.7.0

# Disposable, single-purpose jump box scoped to this challenge's own
# network segment — root-equivalent access here isn't a risk beyond the
# challenge itself, and L2 packet injection genuinely needs it.
RUN useradd -m -s /bin/bash player \
    && echo "player:gh0stcmd" | chpasswd \
    && echo "player ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/player \
    && usermod -aG wireshark player \
    && mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
