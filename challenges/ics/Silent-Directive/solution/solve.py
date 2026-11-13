#!/usr/bin/env python3
# STANDALONE reference solver for "Silent Directive".
# Imports nothing from the builder; hardcodes no key and no flag.
# Inputs: the competitor dist/ artifacts only.
import struct, sys, os
from scapy.all import rdpcap, Raw

HERE = os.path.dirname(__file__)
DIST = os.path.join(HERE, "..", "dist")

# --- keystream, re-derived from reading dist/interceptor.py (not imported) ---
SALT = 0x5350
def keystream(key, pduref, n):
    s = (pduref & 0xFFFF) ^ SALT
    out = bytearray()
    for i in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(key[i % 16] ^ ((s >> 16) & 0xFF))
    return bytes(out)
def stream_only(pduref, n):   # key-independent part
    s = (pduref & 0xFFFF) ^ SALT
    o = bytearray()
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        o.append((s >> 16) & 0xFF)
    return bytes(o)

# --- parse S7comm Write Var packets: (pduref, db, ciphertext value bytes) ---
def parse_writevars(pcap):
    out = []
    for pkt in rdpcap(pcap):
        if not pkt.haslayer(Raw):
            continue
        b = bytes(pkt[Raw].load)
        # TPKT b[0:4], COTP b[4:7], S7 header b[7:17]
        if len(b) < 17 or b[0] != 0x03 or b[7] != 0x32 or b[8] != 0x01:  # TPKT v3, S7 Job
            continue
        pduref = (b[11] << 8) | b[12]
        parlen = (b[13] << 8) | b[14]
        p = 17                                   # start of parameter
        if b[p] != 0x05:                         # Write Var function
            continue
        # param: func b[p], itemcount b[p+1], then item spec at b[p+2]:
        # 12 0a 10 ts len(2) db(2) area addr(3)
        vlen = (b[p+6] << 8) | b[p+7]
        db   = (b[p+8] << 8) | b[p+9]
        d = 17 + parlen                          # start of data section
        # data item: retcode(1) tsize(1) bitlen(2) value(vlen)
        value = b[d+4 : d+4+vlen]
        out.append((pduref, db, value))
    return out

# --- known plaintext: rebuild each DB1 record from the operator console log ---
def known_records(logpath):
    order = ["extraction_rate","core_pressure","coolant_temp","ramp_limit",
             "harmonic_bias","field_margin","duty_cycle","interlock_word"]
    recs = {}
    for line in open(logpath):
        if "WriteVar DB1" not in line:
            continue
        pduref = int(line.split("pdu 0x")[1].split("]")[0], 16)
        kv = dict(tok.split("=") for tok in line.split("<-",1)[1].split())
        recs[pduref] = struct.pack(">8I", *(int(kv[n]) for n in order))
    return recs

def main():
    wv    = parse_writevars(os.path.join(DIST, "extraction_bus.pcap"))
    known = known_records(os.path.join(DIST, "workstation_console.log"))

    # recover the 16-byte director key: for each known DB1 packet,
    # key[i%16] = cipher[i] ^ plain[i] ^ stream[i]
    key = [None]*16
    for pduref, db, cipher in wv:
        if db != 1 or pduref not in known:
            continue
        plain = known[pduref]; st = stream_only(pduref, len(cipher))
        for i in range(len(cipher)):
            kb = cipher[i] ^ plain[i] ^ st[i]
            if key[i % 16] is None:
                key[i % 16] = kb
            assert key[i % 16] == kb, "key inconsistency — algorithm wrong"
    assert all(b is not None for b in key), "insufficient known plaintext to fill key"
    key = bytes(key)
    print("[+] recovered director key:", key.hex())

    # decrypt the covert write (DB7, no console entry)
    for pduref, db, cipher in wv:
        if db == 1:
            continue
        plain = bytes(c ^ k for c, k in zip(cipher, keystream(key, pduref, len(cipher))))
        print(f"[+] decrypted DB{db} directive (pdu 0x{pduref:04x}):")
        print("   ", plain.decode("latin-1"))
        for tok in plain.split(b"::"):
            tok = tok.strip()
            if tok.startswith(b"flag{") and tok.endswith(b"}"):
                print("[+] FLAG:", tok.decode())
                return 0
    print("[-] no flag recovered"); return 1

if __name__ == "__main__":
    sys.exit(main())
