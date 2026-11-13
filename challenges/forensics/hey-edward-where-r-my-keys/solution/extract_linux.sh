#!/bin/bash

BASH_SOURCE_DIR=$(echo $BASH_SOURCE | awk -F'[/]' '{OFS="/"; NF--; print}')
COREDUMP_TAR_FILEPATH="${BASH_SOURCE_DIR}/../dist/core.961.tar.gz"

echo "Decompressing coredump: '$COREDUMP_TAR_FILEPATH'"
tar -xzf $COREDUMP_TAR_FILEPATH


echo "Finding addresses that contain 'iwakuralain@wired.net'."
HEAP_ADDRS=$(gdb -c core.961 --batch -ex "maint info sections" 2> /dev/null | awk '/->/ {print $2}' | awk -F'->' '{print $1, $2}')
HEAP_ADDRS_BEG=($(echo "$HEAP_ADDRS" | awk '{print $1}'))
HEAP_ADDRS_END=($(echo "$HEAP_ADDRS" | awk '{print $2}'))
COMMENT_VAL_ADDRS=()
for idx in "${!HEAP_ADDRS_BEG[@]}"; do
    COMMENT_VAL_ADDRS+=($(gdb -c ./core.961 --batch -ex "find ${HEAP_ADDRS_BEG[idx]}, ${HEAP_ADDRS_END[idx]}, \"iwakuralain@wired.net\"" 2> /dev/null | awk '/^0x/{print $1}'))
done

echo "Finding addresses that point to 'iwakuralain@wired.net'."
KEY_ADDRS=()
for idx in "${!HEAP_ADDRS_BEG[@]}"; do
    for addr in $COMMENT_VAL_ADDRS; do
        COMMENT_PTR_ADDR=$(gdb -c ./core.961 --batch -ex "find ${HEAP_ADDRS_BEG[idx]}, ${HEAP_ADDRS_END[idx]}, ${addr}" 2> /dev/null | awk '/^0x/{print $1}')
        KEY_PTR_ADDR=$(($COMMENT_PTR_ADDR - 0x8))
        if (($KEY_PTR_ADDR <= 0)); then
            continue;
        fi

        KEY_ADDR=$(gdb -c ./core.961 --batch -ex "x/xg ${KEY_PTR_ADDR}" 2> /dev/null | awk '/:/{print $2}')
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


    SHIELDED_PRIVATE_ADDR=$(gdb -c ./core.961 --batch -ex "x/xg ${SHIELDED_PRIVATE_PTR_ADDR}" 2> /dev/null | awk '/:/{print $2}')
    SHIELDED_PRIVATE_LEN=$(gdb -c ./core.961 --batch -ex "x/xg ${SHIELDED_PRIVATE_LEN_ADDR}" 2> /dev/null | awk '/:/{print $2}')

    SHIELD_PREKEY_ADDR=$(gdb -c ./core.961 --batch -ex "x/xg ${SHIELD_PREKEY_PTR_ADDR}" 2> /dev/null | awk '/:/{print $2}')
    SHIELD_PREKEY_LEN=$(gdb -c ./core.961 --batch -ex "x/xg ${SHIELD_PREKEY_LEN_ADDR}" 2> /dev/null | awk '/:/{print $2}')

    gdb -c ./core.961 --batch -ex "dump binary memory ${SHIELDED_PRIVATE_FILEPATH} ${SHIELDED_PRIVATE_ADDR} (${SHIELDED_PRIVATE_ADDR} + ${SHIELDED_PRIVATE_LEN})" > /dev/null 2>&1
    gdb -c ./core.961 --batch -ex "dump binary memory ${SHIELD_PREKEY_FILEPATH} ${SHIELD_PREKEY_ADDR} (${SHIELD_PREKEY_ADDR} + ${SHIELD_PREKEY_LEN})" > /dev/null 2>&1
done
echo "Dumped Shielded Private Key to '${SHIELDED_PRIVATE_FILEPATH}'."
echo "Dumped Shield Prekey to '${SHIELD_PREKEY_FILEPATH}'."
