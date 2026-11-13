BASH_SOURCE_DIR=$(echo $BASH_SOURCE | awk -F'[/]' '{OFS="/"; NF--; print}')
COREDUMP_TAR_FILEPATH="${BASH_SOURCE_DIR}/../dist/core.961.tar.gz"
C_SCRIPT_FILEPATH="${BASH_SOURCE_DIR}/main.c"

echo $C_SCRIPT_FILEPATH

echo "Decompressing coredump: '$COREDUMP_TAR_FILEPATH'"
tar -xzf $COREDUMP_TAR_FILEPATH


echo "Finding addresses that contain 'iwakuralain@wired.net'."
HEAP_ADDRS=$(lldb -c ./core.961 -b -o "memory region --all" | awk '/rw-$/ {print $1}' | awk -F'[-)[]' '{printf "%s %s\\n", $2,$3}')
HEAP_ADDRS_BEG=($(echo $HEAP_ADDRS | awk '{print $1}'))
HEAP_ADDRS_END=($(echo $HEAP_ADDRS | awk '{print $2}'))
COMMENT_VAL_ADDRS=()
for idx in "${!HEAP_ADDRS_BEG[@]}"; do
    COMMENT_VAL_ADDRS+=($(lldb -c ./core.961 -b -o "memory find -s \"iwakuralain@wired.net\" ${HEAP_ADDRS_BEG[idx]} ${HEAP_ADDRS_END[idx]}" | awk '/data found at location:/{print $5}'))
done


echo "Finding addresses that point to 'iwakuralain@wired.net'."
KEY_ADDRS=()
for idx in "${!HEAP_ADDRS_BEG[@]}"; do
    for addr in $COMMENT_VAL_ADDRS; do
        COMMENT_PTR_ADDR=$(lldb -c ./core.961 -b -o "memory find -e ${addr} ${HEAP_ADDRS_BEG[idx]} ${HEAP_ADDRS_END[idx]}" | awk '/data found at location:/{print $5}')
        KEY_PTR_ADDR=$(($COMMENT_PTR_ADDR - 0x8))
        if (($KEY_PTR_ADDR <= 0)); then
            continue;
        fi

        KEY_ADDR=$(lldb -c ./core.961 -b -o "memory read --size 8 --count 1 --format x ${KEY_PTR_ADDR}" | awk -F': ' '/: /{print $2}')
        if (($KEY_ADDR == 0)); then
            continue;
        fi
        KEY_ADDRS+=($KEY_ADDR)
    done
done

echo "Extracting Shielded Private Key and the Shield Prekey."
SHIELDED_PRIVATE_FILEPATH="./shielded_private.bin"
SHIELD_PREKEY_FILEPATH="./shield_prekey.bin"
for addr in $KEY_ADDRS; do
    SHIELDED_PRIVATE_PTR_ADDR=$(($addr + 0x50))
    SHIELDED_PRIVATE_LEN_ADDR=$(($addr + 0x58))

    SHIELD_PREKEY_PTR_ADDR=$(($addr + 0x60))
    SHIELD_PREKEY_LEN_ADDR=$(($addr + 0x68))


    SHIELDED_PRIVATE_ADDR=$(lldb -c ./core.961 -b -o "memory read --size 8 --count 1 --format x ${SHIELDED_PRIVATE_PTR_ADDR}" | awk -F': ' '/: /{print $2}')
    SHIELDED_PRIVATE_LEN=$(lldb -c ./core.961 -b -o "memory read --size 8 --count 1 --format x ${SHIELDED_PRIVATE_LEN_ADDR}" | awk -F': ' '/: /{print $2}')

    SHIELD_PREKEY_ADDR=$(lldb -c ./core.961 -b -o "memory read --size 8 --count 1 --format x ${SHIELD_PREKEY_PTR_ADDR}" | awk -F': ' '/: /{print $2}')
    SHIELD_PREKEY_LEN=$(lldb -c ./core.961 -b -o "memory read --size 8 --count 1 --format x ${SHIELD_PREKEY_LEN_ADDR}" | awk -F': ' '/: /{print $2}')

    lldb -c ./core.961 -b -o "memory read --force --outfile ${SHIELDED_PRIVATE_FILEPATH} --binary --count ${SHIELDED_PRIVATE_LEN} ${SHIELDED_PRIVATE_ADDR}" > /dev/null
    lldb -c ./core.961 -b -o "memory read --force --outfile ${SHIELD_PREKEY_FILEPATH} --binary --count ${SHIELD_PREKEY_LEN} ${SHIELD_PREKEY_ADDR}" > /dev/null
done
echo "Dumped Shielded Private Key to '${SHIELDED_PRIVATE_FILEPATH}'."
echo "Dumped Shield Prekey to '${SHIELD_PREKEY_FILEPATH}'."

echo "Getting latest release of OpenSSH"
curl https://salsa.debian.org/ssh-team/openssh/-/archive/master/openssh-master.tar.gz | tar -xzf -

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
