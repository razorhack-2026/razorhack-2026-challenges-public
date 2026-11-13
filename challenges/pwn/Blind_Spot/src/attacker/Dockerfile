FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        iptables \
        iproute2 \
        net-tools \
        tcpdump \
        nmap \
        dsniff \
        nano \
        sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pymodbus==3.7.0 scapy==2.6.1

# Disposable, single-purpose attack box scoped to this challenge's own
# network segment — root-equivalent access here isn't a risk beyond the
# challenge itself, and the intended technique (ARP spoofing + iptables
# NAT) genuinely needs it.
RUN useradd -m -s /bin/bash player \
    && echo "player:bl1ndsp0t" | chpasswd \
    && echo "player ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/player \
    && mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
