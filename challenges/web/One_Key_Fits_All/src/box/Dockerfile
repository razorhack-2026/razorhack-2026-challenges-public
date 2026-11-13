FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd

RUN pip install --no-cache-dir cryptography==43.0.3

# RazerPowerCo field office machine affected by the VoidCrypt incident.
# Credentials are handed directly to competitors (see challenge.yml /
# README.md) — the point of this challenge is what you do once you're on
# the box, not guessing or cracking SSH creds.
RUN useradd -m -s /bin/bash rpc_tech \
    && echo "rpc_tech:F13ldRecovery!42" | chpasswd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

COPY voidcrypt_recover /home/rpc_tech/voidcrypt_recover
COPY locked_dashboard.bin /home/rpc_tech/locked_dashboard.bin

RUN sed -i 's/\r$//' /home/rpc_tech/voidcrypt_recover \
    && chmod +x /home/rpc_tech/voidcrypt_recover \
    && chown rpc_tech:rpc_tech /home/rpc_tech/voidcrypt_recover /home/rpc_tech/locked_dashboard.bin

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
