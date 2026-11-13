BASH_SOURCE_DIR=$(echo $BASH_SOURCE | awk -F'[/]' '{OFS="/"; NF--; print}')
C_SCRIPT_FILEPATH="${BASH_SOURCE_DIR}/main.c"

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

echo "Configuring OpenSSH"
cd openssh-master
# From this gist: https://gist.github.com/surjikal/aaf0729af90bdc83064b
# Assuming openssl has been installed via `brew install openssl`
BREW_OPENSSL_DIR="$(brew --prefix openssl)"
./configure \
  --prefix="$(pwd)/dist" \
  LDFLAGS="-L${BREW_OPENSSL_DIR}/lib" \
  CPPFLAGS="-I${BREW_OPENSSL_DIR}/include" &&

echo "Replacing 'ssh-keygen.c' with script." &&
cat "../${C_SCRIPT_FILEPATH}" > ssh-keygen.c

echo "Building and running script."
(make ssh-keygen && mv ssh-keygen ../ && cd ../ && ./ssh-keygen && cat ed25519_key) || echo "Build failed"
