#!/usr/bin/env python3
"""
Dead Key -- pcap generator.

Builds a synthetic packet capture of the relay station's local network
segment from just before the operator's death to a few minutes after it.
Story, in order:

  1. Five crew biomonitors each hold an MQTT session to the station's
     telemetry broker, publishing heart rate and O2 on per-crew topics
     every 30 seconds, plus a connection-liveness "heartbeat" counter that
     is a decoy for anyone searching the wrong word. Four crew stay steady.
     One (cm-0417) declines, flatlines to 0, publishes a critical alert
     (the alert text carries no timestamp; the time of death is that
     packet's own capture time), and is then cut off with a bare TCP RST. The other four keep reporting after that moment,
     so the end of the capture is not the answer.
  2. Ops-chat noise (TCP, plaintext): the operator's last messages.
  3. Background chatter (ARP, DNS, NTP, ICMP) so the capture is too big to
     read by scrolling and has to be filtered.

Run:
    python generate_pcap.py [-o ../dist/console_capture.pcap]
"""

import argparse
import random
from datetime import datetime, timezone

from scapy.all import (
    ARP, DNS, DNSQR, DNSRR, Ether, ICMP, IP, NTP, TCP, UDP, Raw, wrpcap,
)
from scapy.contrib.mqtt import MQTT, MQTTConnect, MQTTConnack, MQTTPublish

random.seed(1106)

# ── Cast of hosts ────────────────────────────────────────────────────────────

STATION_CORE = dict(ip="10.13.40.1", mac="02:00:00:00:28:01")      # gateway, DNS, NTP
OPERATOR = dict(ip="10.13.40.10", mac="02:00:00:00:28:0a")         # operator console
IGNITION_GW = dict(ip="10.13.40.30", mac="02:00:00:00:28:1e")      # Ignition gateway
OPS_CHAT = dict(ip="10.13.40.40", mac="02:00:00:00:28:28")         # ops-chat relay
TELEMETRY_BROKER = dict(ip="10.13.40.50", mac="02:00:00:00:28:32")  # MQTT broker

# Crew biomonitors (MQTT clients). cm-0417 is the one who dies.
CREW = [
    dict(badge="cm-0409", ip="10.13.40.21", mac="02:00:00:00:28:15", base_hr=68, port=51801),
    dict(badge="cm-0412", ip="10.13.40.22", mac="02:00:00:00:28:16", base_hr=74, port=51802),
    dict(badge="cm-0417", ip="10.13.40.23", mac="02:00:00:00:28:17", base_hr=72, port=51803, dies=True),
    dict(badge="cm-0421", ip="10.13.40.24", mac="02:00:00:00:28:18", base_hr=79, port=51804),
    dict(badge="cm-0426", ip="10.13.40.25", mac="02:00:00:00:28:19", base_hr=66, port=51805),
]

CHAT_PORT = 6667
MQTT_PORT = 1883

ALERT_TOPIC = "relay07/alerts/critical"
WARN_TOPIC = "relay07/alerts/warning"   # benign decoy from a different crew member

TOD = "2091-11-06_03-22-47"        # UTC capture time of the critical alert = the flag content
FLAG = f"flag{{{TOD}}}"


def ts(h, m, s):
    return datetime(2091, 11, 6, h, m, s, tzinfo=timezone.utc).timestamp()


START = ts(2, 55, 30)
DEATH = ts(3, 22, 47)
END = ts(3, 26, 0)          # capture keeps running a few minutes past the death
SAMPLE_EVERY = 30.0
NTP_EPOCH = 2208988800       # seconds from 1900 (NTP) to 1970 (Unix)


def mqtt_publish(topic, value):
    return bytes(MQTT(type=3) / MQTTPublish(topic=topic, value=str(value)))


# ── TCP stream helper (same shape as Backtrace's gen_pcap.py) ───────────────

class TCPSession:
    """Builds a byte-accurate TCP stream (handshake, pushes, teardown)."""

    def __init__(self, client, cport, server, sport, t0):
        self.c, self.s = client, server
        self.cport, self.sport = cport, sport
        self.t = t0
        self.seq_c = random.randint(1_000_000, 9_000_000)
        self.seq_s = random.randint(1_000_000, 9_000_000)
        self.pkts = []

    def _eth_ip(self, src, dst):
        return Ether(src=src["mac"], dst=dst["mac"]) / IP(src=src["ip"], dst=dst["ip"])

    def _tick(self, dt=0.02):
        self.t += dt
        return self.t

    def handshake(self):
        syn = self._eth_ip(self.c, self.s) / TCP(
            sport=self.cport, dport=self.sport, flags="S", seq=self.seq_c
        )
        syn.time = self._tick()
        self.seq_c += 1

        synack = self._eth_ip(self.s, self.c) / TCP(
            sport=self.sport, dport=self.cport, flags="SA",
            seq=self.seq_s, ack=self.seq_c,
        )
        synack.time = self._tick()
        self.seq_s += 1

        ack = self._eth_ip(self.c, self.s) / TCP(
            sport=self.cport, dport=self.sport, flags="A",
            seq=self.seq_c, ack=self.seq_s,
        )
        ack.time = self._tick()

        self.pkts += [syn, synack, ack]

    def send(self, from_client: bool, payload: bytes, dt=0.05):
        """One PSH/ACK carrying `payload`, ACKed by the other side."""
        src, dst = (self.c, self.s) if from_client else (self.s, self.c)
        sport, dport = (self.cport, self.sport) if from_client else (self.sport, self.cport)
        seq = self.seq_c if from_client else self.seq_s
        ack = self.seq_s if from_client else self.seq_c

        push = self._eth_ip(src, dst) / TCP(
            sport=sport, dport=dport, flags="PA", seq=seq, ack=ack
        ) / Raw(load=payload)
        push.time = self._tick(dt)

        if from_client:
            self.seq_c += len(payload)
        else:
            self.seq_s += len(payload)

        ackpkt = self._eth_ip(dst, src) / TCP(
            sport=dport, dport=sport, flags="A",
            seq=self.seq_s if from_client else self.seq_c,
            ack=self.seq_c if from_client else self.seq_s,
        )
        ackpkt.time = self._tick(dt)

        self.pkts += [push, ackpkt]

    def close(self):
        fin1 = self._eth_ip(self.c, self.s) / TCP(
            sport=self.cport, dport=self.sport, flags="FA",
            seq=self.seq_c, ack=self.seq_s,
        )
        fin1.time = self._tick()
        self.seq_c += 1

        ack1 = self._eth_ip(self.s, self.c) / TCP(
            sport=self.sport, dport=self.cport, flags="A",
            seq=self.seq_s, ack=self.seq_c,
        )
        ack1.time = self._tick()

        fin2 = self._eth_ip(self.s, self.c) / TCP(
            sport=self.sport, dport=self.cport, flags="FA",
            seq=self.seq_s, ack=self.seq_c,
        )
        fin2.time = self._tick()
        self.seq_s += 1

        ack2 = self._eth_ip(self.c, self.s) / TCP(
            sport=self.cport, dport=self.sport, flags="A",
            seq=self.seq_c, ack=self.seq_s,
        )
        ack2.time = self._tick()

        self.pkts += [fin1, ack1, fin2, ack2]

    def abort(self, from_client: bool = True):
        """A bare RST -- the connection dies without a graceful teardown."""
        src, dst = (self.c, self.s) if from_client else (self.s, self.c)
        sport, dport = (self.cport, self.sport) if from_client else (self.sport, self.cport)
        seq = self.seq_c if from_client else self.seq_s
        rst = self._eth_ip(src, dst) / TCP(
            sport=sport, dport=dport, flags="R", seq=seq
        )
        rst.time = self._tick()
        self.pkts.append(rst)


# ── Crew biomonitors ─────────────────────────────────────────────────────────

def hr_for(mon, t):
    jitter = random.randint(-2, 2)
    if mon.get("dies"):
        progress = (t - START) / (DEATH - START)
        return max(40, round(mon["base_hr"] - 15 * progress ** 2) + jitter)
    return mon["base_hr"] + jitter


def o2_for(mon, t):
    jitter = random.choice([-0.1, 0.0, 0.1])
    if mon.get("dies"):
        progress = (t - START) / (DEATH - START)
        return round(20.9 - 2.8 * progress ** 2 + jitter, 1)
    return round(20.9 + jitter, 1)


def monitor_session(idx, mon):
    """One biomonitor's MQTT session: connect, publish vitals until the end
    of the capture (or until death), keepalive pings and a decoy
    "heartbeat" counter along the way."""
    prefix = f"relay07/crew/{mon['badge']}"
    start = START + idx * 4.0
    sess = TCPSession(mon, mon["port"], TELEMETRY_BROKER, MQTT_PORT, start)
    sess.handshake()
    sess.send(True, bytes(MQTT() / MQTTConnect(
        protoname="MQTT", protolevel=4, cleansess=1, klive=60,
        clientId=f"biomon-{mon['badge']}",
    )))
    sess.send(False, bytes(MQTT(type=2) / MQTTConnack(sessPresentFlag=0, retcode=0)))

    end = DEATH if mon.get("dies") else END
    heartbeat = random.randint(100, 900)

    events = []
    k = 0
    t = start + 10
    while t < end - 1:
        events.append((t, "pub", f"{prefix}/vitals/heart_rate", hr_for(mon, t)))
        events.append((t + 0.3, "pub", f"{prefix}/vitals/o2", o2_for(mon, t)))
        if k % 2 == 0:
            heartbeat += 1
            events.append((t + 0.6, "ping", None, None))
            events.append((t + 0.9, "pub", f"{prefix}/link/heartbeat", heartbeat))
        k += 1
        t += SAMPLE_EVERY

    if mon["badge"] == "cm-0421":
        events.append((ts(3, 9, 15), "pub", WARN_TOPIC,
                       "CM-0421 :: ELEVATED STRESS INDEX :: ADVISE REST"))
    events.sort(key=lambda e: e[0])

    for t, kind, topic, value in events:
        sess.t = t
        if kind == "ping":
            sess.send(True, b"\xc0\x00")    # PINGREQ
            sess.send(False, b"\xd0\x00")   # PINGRESP
        else:
            sess.send(True, mqtt_publish(topic, value))

    if mon.get("dies"):
        sess.t = DEATH
        sess.send(True, mqtt_publish(f"{prefix}/vitals/heart_rate", 0))
        # No timestamp in the payload: `strings | grep 2091` finds nothing, and the
        # solver has to read the packet's capture time instead.
        alert = (
            f"CREW {mon['badge'].upper()} :: LIFE SUPPORT FAILURE :: "
            f"NO BIOMETRIC RESPONSE"
        )
        sess.send(True, mqtt_publish(ALERT_TOPIC, alert))
        sess.abort(from_client=True)

    return sess.pkts


# ── Operator traffic (chat) ──────────────────────────────────────────────────

def operator_traffic():
    pkts = []

    chat1 = TCPSession(OPERATOR, 52000, OPS_CHAT, CHAT_PORT, ts(2, 56, 0))
    chat1.handshake()
    chat1.send(True, b"anyone copy? losing atmo on deck 3\r\n")
    chat1.send(False, b"copy, dispatching backup crew, hang tight\r\n")
    pkts += chat1.pkts

    chat2 = TCPSession(OPERATOR, 52001, OPS_CHAT, CHAT_PORT, ts(3, 6, 0))
    chat2.handshake()
    chat2.send(True, b"relay-07 not responding either, going dark soon\r\n")
    chat2.send(False, b"backup crew still 20 out, do what you can\r\n")
    pkts += chat2.pkts

    chat3 = TCPSession(OPERATOR, 52002, OPS_CHAT, CHAT_PORT, ts(3, 19, 30))
    chat3.handshake()
    chat3.send(True, b"last log burst going out now, tell my sister I'm sorry\r\n")
    chat3.close()
    pkts += chat3.pkts

    return pkts


# ── Background chatter ───────────────────────────────────────────────────────

LAN_HOSTS = [OPERATOR, IGNITION_GW, OPS_CHAT, TELEMETRY_BROKER] + CREW
DNS_NAMES = [
    ("ignition-gw.razorpowerco.local", IGNITION_GW["ip"]),
    ("telemetry.relay07.razorpowerco.local", TELEMETRY_BROKER["ip"]),
    ("ops-chat.relay07.razorpowerco.local", OPS_CHAT["ip"]),
    ("ntp.relay07.razorpowerco.local", STATION_CORE["ip"]),
]


def _eth(src, dst):
    return Ether(src=src["mac"], dst=dst["mac"]) / IP(src=src["ip"], dst=dst["ip"])


def _stamp(pkt, t):
    pkt.time = t
    return pkt


def background_noise():
    pkts = []
    t_end = END

    # ARP who-has / is-at
    t = START - 90
    while t < t_end:
        asker, target = random.sample(LAN_HOSTS, 2)
        req = Ether(src=asker["mac"], dst="ff:ff:ff:ff:ff:ff") / ARP(
            op=1, hwsrc=asker["mac"], psrc=asker["ip"], pdst=target["ip"])
        rep = Ether(src=target["mac"], dst=asker["mac"]) / ARP(
            op=2, hwsrc=target["mac"], psrc=target["ip"],
            hwdst=asker["mac"], pdst=asker["ip"])
        pkts += [_stamp(req, t), _stamp(rep, t + 0.002)]
        t += random.uniform(30, 60)

    # DNS lookups against the station core
    t = START - 60
    while t < t_end:
        host = random.choice(LAN_HOSTS)
        name, answer = random.choice(DNS_NAMES)
        qid = random.randint(1, 65000)
        sport = random.randint(40000, 60000)
        q = _eth(host, STATION_CORE) / UDP(sport=sport, dport=53) / DNS(
            id=qid, rd=1, qd=DNSQR(qname=name))
        r = _eth(STATION_CORE, host) / UDP(sport=53, dport=sport) / DNS(
            id=qid, qr=1, aa=1, rd=1, ra=1, qd=DNSQR(qname=name),
            an=DNSRR(rrname=name, type="A", ttl=300, rdata=answer))
        pkts += [_stamp(q, t), _stamp(r, t + 0.004)]
        t += random.uniform(60, 120)

    # NTP polling
    t = START - 30
    while t < t_end:
        host = random.choice(LAN_HOSTS)
        sport = random.randint(40000, 60000)
        # Explicit NTP times (scapy would stamp the real wall clock, leaking 2026 into a
        # 2091 capture and making the output differ on every run).
        q = _eth(host, STATION_CORE) / UDP(sport=sport, dport=123) / NTP(
            version=4, mode=3, ref=0, orig=0, recv=0, sent=t + NTP_EPOCH)
        r = _eth(STATION_CORE, host) / UDP(sport=123, dport=sport) / NTP(
            version=4, mode=4, stratum=2, ref=t - 10 + NTP_EPOCH, orig=t + NTP_EPOCH,
            recv=t + 0.003 + NTP_EPOCH, sent=t + 0.004 + NTP_EPOCH)
        pkts += [_stamp(q, t), _stamp(r, t + 0.006)]
        t += random.uniform(90, 150)

    # the operator's console pinging the broker
    t = START - 45
    seq = 1
    while t < t_end:
        ident = 0x2a2a
        payload = Raw(load=b"relay07-link-check")
        req = _eth(OPERATOR, TELEMETRY_BROKER) / ICMP(type=8, id=ident, seq=seq) / payload
        rep = _eth(TELEMETRY_BROKER, OPERATOR) / ICMP(type=0, id=ident, seq=seq) / payload
        pkts += [_stamp(req, t), _stamp(rep, t + 0.001)]
        seq += 1
        t += random.uniform(45, 75)

    return pkts


# ── Assembly ──────────────────────────────────────────────────────────────────

def build_capture():
    pkts = []
    for idx, mon in enumerate(CREW):
        pkts += monitor_session(idx, mon)
    pkts += operator_traffic()
    pkts += background_noise()
    return pkts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../dist/console_capture.pcap")
    args = ap.parse_args()

    pkts = build_capture()
    pkts.sort(key=lambda p: p.time)
    wrpcap(args.out, pkts)
    print(f"[+] wrote {len(pkts)} packets to {args.out}")
    print(f"[+] flag: {FLAG}")


if __name__ == "__main__":
    main()
