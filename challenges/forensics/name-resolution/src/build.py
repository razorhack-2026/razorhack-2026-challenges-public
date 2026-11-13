#!/usr/bin/env python3
"""
Name Resolution — build script (GM-only).

Generates dist/capture.pcap: a short span of a KOT console's network traffic in
which a compromised process exfiltrates a payload over DNS. Most of the DNS
traffic is ordinary internal name resolution (*.kot.rpc); the exfil rides a run
of lookups to one external domain, where each query's leading subdomain label
carries a sequence number and a base32 chunk of the payload.

Reassembling the exfil labels in sequence order and base32-decoding them yields
a short text blob containing the flag.

This file contains the flag and MUST NOT ship to competitors. Only dist/ ships.
"""
import base64
import random

from scapy.all import DNS, DNSQR, DNSRR, IP, UDP, Ether, wrpcap

FLAG = "flag{just_a_d1fferent_kind_of_lookup}"

# What the exfil actually carries: a little context wrapper around the flag, so
# the decoded blob reads like something a tool dumped, not a bare string.
PAYLOAD = (
    "KOT-CONSOLE-7 uplink dump\n"
    "dest: off-manifest vessel beacon (hull KX9 - not on the convoy roster)\n"
    'handler: "the helper" / svc-onboard\n'
    f"{FLAG}\n"
).encode()

EXFIL_DOMAIN = "uplink.hull-kx9.beacon"   # an unknown vessel's beacon - the tell
RESOLVER = "10.4.0.2"                         # the ship's internal resolver
CONSOLE = "10.4.7.31"                         # the compromised console

# Fixed, locally administered MACs ("KOT" in bytes 2-4). Without them scapy
# fills in the build machine's own MAC and its gateway's, so the pcap would
# change from host to host and carry real hardware addresses.
RESOLVER_MAC = "02:4b:4f:54:00:02"
CONSOLE_MAC = "02:4b:4f:54:07:1f"

# Ordinary internal hostnames the console legitimately resolves.
BENIGN = [
    "nav.kot.rpc", "telemetry.kot.rpc", "ntp.kot.rpc", "update.kot.rpc",
    "lifesupport.kot.rpc", "ops-portal.kot.rpc", "mail.kot.rpc",
    "docking.kot.rpc", "reactor-hmi.kot.rpc", "crew-wiki.kot.rpc",
]

random.seed(20261102)  # deterministic build


def b32(data: bytes) -> str:
    return base64.b32encode(data).decode().lower().rstrip("=")


def dns_query(t, qname, txid):
    pkt = (
        Ether(src=CONSOLE_MAC, dst=RESOLVER_MAC)
        / IP(src=CONSOLE, dst=RESOLVER)
        / UDP(sport=random.randint(49152, 65535), dport=53)
        / DNS(id=txid, rd=1, qd=DNSQR(qname=qname, qtype="A"))
    )
    pkt.time = t
    return pkt


def dns_reply(t, qname, txid, answer_ip):
    pkt = (
        Ether(src=RESOLVER_MAC, dst=CONSOLE_MAC)
        / IP(src=RESOLVER, dst=CONSOLE)
        / UDP(sport=53, dport=random.randint(49152, 65535))
        / DNS(id=txid, qr=1, rd=1, ra=1,
              qd=DNSQR(qname=qname, qtype="A"),
              an=DNSRR(rrname=qname, type="A", ttl=60, rdata=answer_ip))
    )
    pkt.time = t
    return pkt


def main():
    # Build the exfil label list: "<seq>-<chunk>.<EXFIL_DOMAIN>".
    blob = b32(PAYLOAD)
    chunk_len = 24
    chunks = [blob[i:i + chunk_len] for i in range(0, len(blob), chunk_len)]
    exfil_names = [f"{i:02d}-{c}.{EXFIL_DOMAIN}" for i, c in enumerate(chunks)]

    packets = []
    t = 1_762_100_000.0  # arbitrary epoch base for the capture
    txid = random.randint(0, 0xFFFF)

    # Interleave: a few benign lookups, then an exfil lookup, repeat — so a
    # naive "look at all DNS" view is noisy and the run to one odd external
    # domain is what stands out. Exfil queries stay in payload order in time.
    exfil_iter = iter(exfil_names)
    exfil_done = False
    while not exfil_done:
        # 1-3 benign lookups
        for _ in range(random.randint(1, 3)):
            name = random.choice(BENIGN)
            txid = (txid + 1) & 0xFFFF
            t += random.uniform(0.05, 0.6)
            packets.append(dns_query(t, name, txid))
            t += random.uniform(0.002, 0.03)
            packets.append(dns_reply(t, name, txid, f"10.4.{random.randint(1,9)}.{random.randint(2,254)}"))
        # one exfil lookup (every odd query resolves to the same off-ship relay
        # link - a vessel uplink address, not a public-internet host; the repeat
        # is itself a tell)
        try:
            name = next(exfil_iter)
        except StopIteration:
            exfil_done = True
            continue
        txid = (txid + 1) & 0xFFFF
        t += random.uniform(0.05, 0.4)
        packets.append(dns_query(t, name, txid))
        t += random.uniform(0.002, 0.03)
        packets.append(dns_reply(t, name, txid, "100.64.9.9"))

    # a trailing tail of pure benign traffic so the capture doesn't end on exfil
    for _ in range(8):
        name = random.choice(BENIGN)
        txid = (txid + 1) & 0xFFFF
        t += random.uniform(0.05, 0.6)
        packets.append(dns_query(t, name, txid))
        t += random.uniform(0.002, 0.03)
        packets.append(dns_reply(t, name, txid, f"10.4.{random.randint(1,9)}.{random.randint(2,254)}"))

    wrpcap("dist/capture.pcap", packets)
    print(f"wrote dist/capture.pcap: {len(packets)} packets, "
          f"{len(chunks)} exfil queries over {EXFIL_DOMAIN}")


if __name__ == "__main__":
    main()
