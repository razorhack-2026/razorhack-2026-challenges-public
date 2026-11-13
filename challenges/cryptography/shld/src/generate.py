#!/usr/bin/env python3
"""SHLD artifact generator. Writes dist/shield_phase.bin and shield_notes.txt.

Encryption order: plaintext -> Vigenere -> AES-128-ECB. The AES step shells out
to openssl so the blob decrypts with any standard AES-128-ECB tool.

Flag: flag{shld_schum4nn_r3s0n4nc3}
"""
import hashlib
import os
import subprocess
import sys

FLAG = 'flag{stop_touching_my_things}'
PLAINTEXT = f"SHIELD_ON|freq=7.83Hz|token={FLAG}"
VIGENERE_KEY = "MICROBOT"
AES_KEY_SEED = b"shield"

NOTES = """# PHASE INVERTER LOG - RELIANT
# STATUS: HARMONICS DRIFTING
# NOTE FROM SYSOP: "they stacked a notebook cipher under a block cipher again"

[LAYER A - OUTER]
A block cipher protects this layer. Its key is derived from the subsystem name.

[LAYER B - INNER]
A schoolbook cipher uses the name stencilled on each crate shipped with this swarm.

[LAYER C - DECOY]
freq=432Hz is a joke. Do not tune to it.
"""


def vigenere_encrypt(pt: str, key: str) -> str:
    out = []
    ki = 0
    for c in pt:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            k = ord(key[ki % len(key)].upper()) - ord("A")
            out.append(chr((ord(c) - base + k) % 26 + base))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


def aes128_ecb_encrypt(plaintext: bytes, key: bytes) -> bytes:
    if len(key) != 16:
        raise SystemExit("AES-128 key must be 16 bytes")
    try:
        proc = subprocess.run(
            ["openssl", "enc", "-aes-128-ecb", "-K", key.hex(), "-nosalt"],
            input=plaintext,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        raise SystemExit("openssl is required to generate the SHLD blob") from None
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr.decode("utf-8", errors="replace"))
        raise SystemExit("openssl enc failed") from exc
    return proc.stdout


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    os.makedirs(out_dir, exist_ok=True)

    layer1 = vigenere_encrypt(PLAINTEXT, VIGENERE_KEY)
    key = hashlib.md5(AES_KEY_SEED).digest()
    ct = aes128_ecb_encrypt(layer1.encode("ascii"), key)

    bin_path = os.path.join(out_dir, "shield_phase.bin")
    with open(bin_path, "w", encoding="ascii") as f:
        f.write(ct.hex() + "\n")

    notes_path = os.path.join(out_dir, "shield_notes.txt")
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(NOTES)

    print(f"wrote dist/shield_phase.bin ({len(ct)} bytes ciphertext)")
    print(f"wrote dist/shield_notes.txt")
    print(f"flag: {FLAG}")


if __name__ == "__main__":
    main()
