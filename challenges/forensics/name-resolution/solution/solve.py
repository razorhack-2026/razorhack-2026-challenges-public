#!/usr/bin/env python3
"""
Name Resolution — reference solver (GM-only).

Reads ONLY the competitor handout (dist/capture.pcap). Imports nothing from the
build script and hardcodes no answer: it recovers the flag purely from the
capture, the way a competitor would.

Intended path:
  1. Open the capture; notice most DNS is internal (*.kot.rpc) but there is a
     run of lookups to one external domain with random-looking subdomains.
  2. That domain's queries each start with "<seq>-<chunk>". Collect them,
     order by seq, strip the seq, concatenate the chunks.
  3. base32-decode the concatenation -> a text blob containing the flag.
"""
import base64
import re
import sys

from scapy.all import DNS, DNSQR, rdpcap

EXFIL_SUFFIX = "hull-kx9.beacon"


def main(path):
    pkts = rdpcap(path)

    # Pull every DNS *query* name seen in the capture.
    names = []
    for p in pkts:
        if p.haslayer(DNS) and p.getlayer(DNS).qr == 0 and p.haslayer(DNSQR):
            qn = p[DNSQR].qname.decode().rstrip(".")
            names.append(qn)

    # Keep the ones to the odd external domain; parse "<seq>-<chunk>" head label.
    seq_chunks = []
    pat = re.compile(r"^(\d+)-([a-z2-7]+)$")
    for qn in names:
        if not qn.endswith(EXFIL_SUFFIX):
            continue
        head = qn.split(".", 1)[0]
        m = pat.match(head)
        if m:
            seq_chunks.append((int(m.group(1)), m.group(2)))

    seq_chunks.sort(key=lambda x: x[0])
    blob = "".join(c for _, c in seq_chunks)

    # base32 needs padding back to a multiple of 8.
    pad = (-len(blob)) % 8
    decoded = base64.b32decode(blob.upper() + "=" * pad)
    text = decoded.decode(errors="replace")

    print(text)
    m = re.search(r"flag\{[^}]+\}", text)
    if m:
        print("FLAG:", m.group(0))
        return 0
    print("no flag recovered", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "../dist/capture.pcap"))
