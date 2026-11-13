#!/usr/bin/env python3
"""Build dist/interlock.enc -- the sealed blob competitors decrypt once CPA has
given them the interlock key.

GM-only. The flag is written into the blob here and nowhere else in dist/.

The sealing key is SHA-256(device_key)[:16], NOT the device key itself. The rig
is an encryption oracle under the device key, so sealing directly under it
would let a solver skip the side channel entirely if the mode ever allowed it;
the derivation makes that structurally impossible. The container format is
public -- it is stated in the blob's own plaintext envelope, because
competitors cannot be expected to guess it, and publishing it gives away
nothing about the key.

    python gen_interlock.py --flag 'flag{...}' --out ../dist/interlock.enc
"""
import argparse
import hashlib
import os
import pathlib
import sys

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

HERE = pathlib.Path(__file__).resolve().parent

# Plaintext envelope. The blob has to say how it is sealed -- nobody recovers a
# 16-byte key and then guesses "SHA-256 it and read the first 16 bytes as a CBC
# IV". Stating the construction gives away nothing about the key, and it keeps
# the recipe in the artifact instead of in a separate handout.
ENVELOPE = (
    b"RPC-SEALED-RECORD v2\n"
    b"unit: RPC-IC220\n"
    b"kdf: sha256(interlock-key)[0:16]\n"
    b"cipher: aes-128-cbc\n"
    b"iv: first 16 bytes of payload\n"
    b"--\n"
)

# Sealed body. Decrypting to this header tells a solver the key is right.
HEADER = (
    b"RPC-INTERLOCK-AUTH v2\n"
    b"unit: RPC-IC220\n"
    b"role: reactor primary interlock\n"
    b"auth: "
)


def seal(flag: str, device_key: bytes) -> bytes:
    sealing_key = hashlib.sha256(device_key).digest()[:16]
    iv = os.urandom(16)
    body = HEADER + flag.encode() + b"\n"
    ct = AES.new(sealing_key, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    return ENVELOPE + iv + ct


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flag", required=True)
    ap.add_argument("--key", default=None,
                    help="device key as hex (default: src/device_key.txt)")
    ap.add_argument("--out",
                    default=str(HERE.parent / "dist" / "interlock.enc"))
    args = ap.parse_args()

    if not args.flag.startswith("flag{") or not args.flag.endswith("}"):
        print(f"refusing to seal a non-flag-shaped value: {args.flag!r}",
              file=sys.stderr)
        return 1

    key_hex = args.key or (HERE / "device_key.txt").read_text().strip()
    device_key = bytes.fromhex(key_hex)
    if len(device_key) != 16:
        print(f"device key must be 16 bytes, got {len(device_key)}",
              file=sys.stderr)
        return 1

    blob = seal(args.flag, device_key)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    print(f"wrote {out} ({len(blob)} bytes)")
    print(f"sealing key = SHA256(device_key)[:16] = "
          f"{hashlib.sha256(device_key).hexdigest()[:32]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
