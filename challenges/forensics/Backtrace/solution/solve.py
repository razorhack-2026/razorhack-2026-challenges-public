#!/usr/bin/env python3
"""
Backtrace -- reference solution / acceptance test.

Walks the same trace a contestant would do by hand in Wireshark, but
scripted, so it can be run as a regression test against the dist pcap:

  1. Find the malicious Modbus write (FC05, coil 0, value 0) and its
     timestamp/source host.
  2. Follow the Telnet stream into eng-console around that time and
     recover the credentials used.
  3. Search the rest of the capture for those same credentials showing
     up somewhere else -- the FTP upload of a gzip-compressed backup --
     and pull the flag out of the decompressed file.

Usage:
    python solve.py [path/to/kestrel_shipnet.pcap]
"""

import gzip
import re
import sys

from scapy.all import rdpcap, TCP, Raw


def reassemble_stream(pkts, port):
    """Concatenate Raw payloads for a TCP conversation on the given port,
    in capture order (good enough for these single, non-overlapping flows)."""
    data = b""
    for p in pkts:
        if TCP in p and Raw in p and (p[TCP].sport == port or p[TCP].dport == port):
            data += bytes(p[Raw].load)
    return data


def find_malicious_write(pkts):
    for p in pkts:
        if TCP in p and Raw in p and (p[TCP].sport == 502 or p[TCP].dport == 502):
            raw = bytes(p[Raw].load)
            # Modbus ADU: transId(2) protoId(2) len(2) unitId(1) funcCode(1) ...
            if len(raw) >= 8 and raw[7] == 0x05:
                return p, raw
    return None, None


def main():
    pcap_path = sys.argv[1] if len(sys.argv) > 1 else "../dist/kestrel_shipnet.pcap"
    pkts = rdpcap(pcap_path)

    write_pkt, raw = find_malicious_write(pkts)
    if write_pkt is None:
        print("[-] Could not find the malicious Modbus write (FC05).")
        sys.exit(1)

    print(f"[+] Malicious write at t={write_pkt.time}  src={write_pkt[TCP].sport}->{write_pkt[TCP].dport}")
    print(f"    ADU bytes: {raw.hex()}  (unitId={raw[6]}, funcCode={raw[7]}, addr={int.from_bytes(raw[8:10], 'big')}, value={int.from_bytes(raw[10:12], 'big')})")

    telnet = reassemble_stream(pkts, 23).decode(errors="replace")
    print("\n[+] Telnet stream to eng-console:")
    print(telnet)

    m = re.search(r"login:\s*(\S+).*?Password:\s*(\S+)", telnet, re.S)
    if not m:
        print("[-] Could not parse credentials out of the telnet stream.")
        sys.exit(1)
    username, password = m.group(1), m.group(2)
    print(f"[+] Recovered credentials from telnet: {username} / {password}")

    # Find the FTP data channel: any TCP stream containing gzip magic bytes.
    gz_ports = set()
    for p in pkts:
        if TCP in p and Raw in p and bytes(p[Raw].load).startswith(b"\x1f\x8b"):
            gz_ports.add(p[TCP].sport)
            gz_ports.add(p[TCP].dport)

    if not gz_ports:
        print("[-] No gzip-compressed data channel found in the capture.")
        sys.exit(1)

    flag = None
    for port in gz_ports:
        blob = reassemble_stream(pkts, port)
        try:
            content = gzip.decompress(blob).decode()
        except OSError:
            continue
        if username in content and password in content:
            print(f"\n[+] Found matching leaked backup on port {port}:")
            print(content)
            m2 = re.search(r"flag\{[^}]+\}", content)
            if m2:
                flag = m2.group(0)

    if not flag:
        print("[-] Could not locate the flag in any decompressed FTP payload.")
        sys.exit(1)

    print(f"\n[+] FLAG: {flag}")


if __name__ == "__main__":
    main()
