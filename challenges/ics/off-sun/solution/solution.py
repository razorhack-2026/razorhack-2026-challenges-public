#!/usr/bin/env python3
"""
Off-Sun — reference solver (RazorHack 2026, ICS, hard).

Runs against ONLY dist/array_ctrl.pcap. Stdlib only. Reproduces the intended solve:

  1. The capture is Modbus, but on TCP 1502 — "Decode As -> Modbus" in Wireshark.
     (This parser dissects it directly.)
  2. The controller 10.20.7.40 is the Modbus server; everyone else polls or writes it.
     Reads (FC03) are the noise floor. The writes (FC06) are what matter.
  3. Two hosts write: the engineering workstation and — sharing the SAME IP
     (10.20.7.11) but a DIFFERENT MAC — a rogue device. Both write the elevation
     SETPOINT register (111), so neither IP nor register isolates the rogue; the
     MAC does. One IP with two MACs is the spoofing tell.
  4. The rogue's writes carry one ASCII byte each in the register value; in order
     they spell the flag. (The legit setpoint writes decode to gibberish, which is
     how you confirm you picked the right MAC.)
"""
import os
import struct
from collections import defaultdict

SERVER_IP = "10.20.7.40"     # the Modbus server (determined by inspecting the capture)
REG_SETPOINT = 0x006F        # 111
FC_WRITE_SINGLE = 0x06


def iter_packets(path):
    d = open(path, "rb").read()
    assert struct.unpack("<I", d[:4])[0] == 0xa1b2c3d4, "not a little-endian pcap"
    off = 24
    while off + 16 <= len(d):
        _sec, _usec, caplen, _orig = struct.unpack("<IIII", d[off:off + 16])
        off += 16
        yield d[off:off + caplen]
        off += caplen


def parse(frame):
    """Return dict for an FC06 write *request* (addressed to the server), else None."""
    if len(frame) < 34 or frame[12:14] != b"\x08\x00":
        return None
    if frame[23] != 6:  # IP proto != TCP
        return None
    ihl = (frame[14] & 0x0F) * 4
    src_ip = ".".join(str(b) for b in frame[26:30])
    dst_ip = ".".join(str(b) for b in frame[30:34])
    if dst_ip != SERVER_IP:      # requests go TO the server; this drops the echoed responses
        return None
    src_mac = frame[6:12].hex(":")
    ip_end = 14 + ihl
    tcp_off = ((frame[ip_end + 12] >> 4) & 0x0F) * 4
    payload = frame[ip_end + tcp_off:]
    if len(payload) < 12 or struct.unpack(">H", payload[2:4])[0] != 0:  # MBAP proto id
        return None
    if payload[7] != FC_WRITE_SINGLE:
        return None
    reg, value = struct.unpack(">HH", payload[8:12])
    return dict(src_ip=src_ip, src_mac=src_mac, reg=reg, value=value)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    pcap = os.path.normpath(os.path.join(here, "..", "dist", "array_ctrl.pcap"))

    ip_to_macs = defaultdict(set)
    setpoint_writes = []  # (src_ip, src_mac, value) in capture order
    for frame in iter_packets(pcap):
        w = parse(frame)
        if not w:
            continue
        ip_to_macs[w["src_ip"]].add(w["src_mac"])
        if w["reg"] == REG_SETPOINT:
            setpoint_writes.append((w["src_ip"], w["src_mac"], w["value"]))

    # the spoofing tell: an IP that presents more than one MAC
    spoofed = {ip: macs for ip, macs in ip_to_macs.items() if len(macs) > 1}
    print("writers (ip -> macs):", {ip: sorted(m) for ip, m in ip_to_macs.items()})
    print("IP(s) with multiple MACs (spoof tell):", {ip: sorted(m) for ip, m in spoofed.items()})

    # group setpoint writes by MAC; the group that decodes to a flag is the rogue's
    by_mac = defaultdict(list)
    for _ip, mac, value in setpoint_writes:
        by_mac[mac].append(value)

    flag = None
    for mac, values in by_mac.items():
        text = bytes(v & 0xFF for v in values).decode(errors="replace")
        marker = "  <-- flag" if text.startswith("flag{") else ""
        print(f"  MAC {mac}: {text!r}{marker}")
        if text.startswith("flag{"):
            flag = text

    print("recovered flag:", flag)
    return flag


if __name__ == "__main__":
    main()
