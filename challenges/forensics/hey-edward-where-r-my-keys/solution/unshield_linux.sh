#!/bin/bash

BASH_SOURCE_DIR=$(echo $BASH_SOURCE | awk -F'[/]' '{OFS="/"; NF--; print}')
C_SCRIPT_FILEPATH="${BASH_SOURCE_DIR}/script.c"

if [! -f "./shielded_private.bin"]; then
    echo "'shielded_private.bin' does not exist"
    exit
fi

if [! -f "./shield_prekey.bin"]; then
    echo "'shielded_prekey.bin' does not exist"
    exit
fi

echo "Getting latest release of OpenSSH"
curl https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-10.4p1.tar.gz | tar -xzf -

echo "Replacing 'ssh-keygen.c' with script." &&
cat "../${C_SCRIPT_FILEPATH}" > ssh-keygen.c

echo "Configuring OpenSSH"
cd openssh-10.4p1
./configure

echo "Building and running script."
(make ssh-keygen && mv ssh-keygen ../ && cd ../ && ./ssh-keygen && cat id_ed25519) || echo "Build failed"
