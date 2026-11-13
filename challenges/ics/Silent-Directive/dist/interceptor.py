#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# rpc_fieldbus_shim.py  ("interceptor")
# Recovered from ICARUS extraction-control segment, engineering VLAN.
# Author string in binary: "Dr. Rootkit"
#
# Inline confidentiality shim for the S7comm extraction bus. Sits between the
# engineering workstation and the extraction PLC and re-encodes the *value*
# field of every "Write Var" so a passive tap on the bus sees only ciphertext.
# The PLC shares the director key and decodes transparently.
#
# NOTE (recovered config, redacted): the 16-byte director key was loaded at
# runtime from  /etc/rpc/.director_key  — NOT present in this recovered copy.
# ---------------------------------------------------------------------------

# DB1 = master extraction profile (what operators push from the console):
#   off  0  u32  extraction_rate
#   off  4  u32  core_pressure
#   off  8  u32  coolant_temp
#   off 12  u32  ramp_limit
#   off 16  u32  harmonic_bias
#   off 20  u32  field_margin
#   off 24  u32  duty_cycle
#   off 28  u32  interlock_word
# DB7 = maintenance scratch (director-only).

SALT = 0x5350  # 'SP' — bus segment tag, mixed into the per-frame stream seed

def _stream(pduref, n):
    # per-frame keystream basis: a glibc-style LCG seeded from the S7comm
    # Protocol-Data-Unit reference of THIS frame (so every frame differs).
    s = (pduref & 0xFFFF) ^ SALT
    out = bytearray()
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((s >> 16) & 0xFF)
    return out

def keystream(key, pduref, n):
    # value byte i is XORed with key[i % 16] XOR stream[i].
    st = _stream(pduref, n)
    return bytes(key[i % 16] ^ st[i] for i in range(n))

def encode_value(key, pduref, value_bytes):
    ks = keystream(key, pduref, len(value_bytes))
    return bytes(b ^ k for b, k in zip(value_bytes, ks))

decode_value = encode_value  # XOR is symmetric

if __name__ == "__main__":
    # Live path (needs the director key file, not recovered):
    with open("/etc/rpc/.director_key", "rb") as f:
        KEY = f.read(16)
    # ... inline hook rewrites DB1 writes and emits DB7 directives ...
    raise SystemExit("director key unavailable in recovered copy")
