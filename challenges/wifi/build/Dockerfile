FROM debian:bookworm

# Install packages
RUN apt-get update && apt-get upgrade -y && apt-get dist-upgrade -y && DEBIAN_FRONTEND=noninteractive
RUN apt-get install --fix-missing  -y iputils-ping
RUN apt-get install --fix-missing  -y openssh-server
RUN apt-get install --fix-missing  -y procps
RUN apt-get install --fix-missing  -y wpasupplicant
RUN apt-get install --fix-missing  -y isc-dhcp-common
RUN apt-get install --fix-missing  -y isc-dhcp-client
RUN apt-get install --fix-missing  -y arping
RUN apt-get install --fix-missing  -y vim
RUN apt-get install --fix-missing  -y screen
RUN apt-get install --fix-missing  -y pkg-config
RUN apt-get install --fix-missing  -y libnl-3-dev
RUN apt-get install --fix-missing  -y gcc
RUN apt-get install --fix-missing  -y libssl-dev
RUN apt-get install --fix-missing  -y libnl-genl-3-dev
RUN apt-get install --fix-missing  -y python3
RUN apt-get install --fix-missing  -y git
RUN apt-get install --fix-missing  -y wireless-tools
RUN apt-get install --fix-missing  -y make
RUN apt-get install --fix-missing  -y wget
RUN apt-get install --fix-missing  -y nano
RUN apt-get install --fix-missing  -y aircrack-ng
RUN apt-get install --fix-missing  -y net-tools
RUN apt-get install --fix-missing  -y nmap
RUN apt-get install --fix-missing  -y curl
RUN apt-get install --fix-missing  -y netcat-openbsd
RUN apt-get install --fix-missing  -y postgresql-client
RUN apt-get install --fix-missing  -y w3m
RUN apt-get install --fix-missing  -y lynx
RUN apt-get install --fix-missing  -y bash-completion
RUN apt-get install --fix-missing  -y tcpdump
RUN apt-get install --fix-missing  -y python3-pip
RUN apt-get install --fix-missing  -y python3-scapy
RUN apt-get install --fix-missing  -y hostapd
RUN apt-get install --fix-missing  -y macchanger
RUN apt-get install --fix-missing  -y pciutils

RUN apt-get install --fix-missing  -y locales
RUN sed -i '/en_US.UTF-8/s/^# //' /etc/locale.gen
RUN locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV TERM=xterm-256color

# Make home directory
RUN mkdir /home/rh
RUN chsh -s /bin/bash root
RUN cp /etc/skel/.bashrc /root/.bashrc
RUN echo "cd /home/rh" >> /root/.bashrc

# Colored prompt: green user@host, blue cwd
RUN echo "PS1='\[\e[1;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\\$ '" >> /root/.bashrc

# Download rockyou.txt wordlist for cracking
RUN wget https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt -P /home/rh

# Copy wpa_supplicant config for bridge connection
COPY content/connection.conf /home/rh

# Copy wacker stuff
# RUN mkdir /home/rh/wacker
# COPY content/wacker/wpa_supplicant /home/rh/wacker/wpa_supplicant-2.10/wpa_supplicant/
# COPY content/wacker/split.sh /home/rh/wacker
# COPY content/wacker/wacker.py /home/rh/wacker

# Remove login message
RUN touch ~/.hushlogin

# Set up SSH access
RUN echo 'root:password' | chpasswd
COPY content/sshd_config /etc/ssh/sshd_config
RUN mkdir -p /run/sshd

CMD ["/usr/sbin/sshd", "-D"]

EXPOSE 22/tcp
