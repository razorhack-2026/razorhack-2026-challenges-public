#!/usr/bin/env python3
"""
Off-Sun — capture generator (RazorHack 2026, ICS, hard).

Writes dist/array_ctrl.pcap: a Modbus capture from a solar-array control segment.

Design (see solution/SOLUTION.md for the full writeup):
  * Modbus runs on TCP 1502, NOT the well-known 502 — Wireshark won't auto-dissect
    it until the analyst does "Decode As -> Modbus".
  * An HMI and a historian poll pointing/power registers read-only (the noise floor).
  * The engineering workstation (10.20.7.11) legitimately writes the elevation
    SETPOINT register now and then — small in-range values.
  * A rogue device also writes the SETPOINT register, spoofing the engineering
    workstation's IP (10.20.7.11) but with a different MAC. Its writes carry one
    flag byte each (raw ASCII in the register value), and they are what slewed the
    arrays off-sun. Same IP + same register as the legit writes means you can't
    isolate them by IP or register — the only clean discriminator is the MAC.

Pure stdlib — no scapy. Deterministic on --seed.
"""
import argparse
import os
import struct

FLAG = "flag{d0nt_l00k_d1r3ctly_4t_th3_sun}"

MODBUS_PORT = 1502  # non-standard on purpose

# --- hosts on the control segment (IP, MAC, client port) ---------------------
CTRL  = dict(ip="10.20.7.40", mac=bytes.fromhex("0080f4aabbcc"), port=MODBUS_PORT)  # array controller (server)
HMI   = dict(ip="10.20.7.10", mac=bytes.fromhex("001b1b112233"), port=51000)        # operator HMI (polls)
HIST  = dict(ip="10.20.7.20", mac=bytes.fromhex("001b1b778899"), port=51200)        # historian (polls more)
ENGWS = dict(ip="10.20.7.11", mac=bytes.fromhex("001b1b445566"), port=51500)        # engineering ws (legit writes)
# rogue spoofs the engineering workstation's IP but keeps its own MAC:
ROGUE = dict(ip="10.20.7.11", mac=bytes.fromhex("525400deadbe"), port=52000)

# --- register map (documented in SOLUTION.md, NOT shipped) -------------------
REG_AZIMUTH   = 0x0064  # 100 read-only pointing feedback
REG_ELEVATION = 0x0065  # 101 read-only pointing feedback
REG_POWER     = 0x0066  # 102 read-only array output
REG_TEMP      = 0x0067  # 103 read-only panel temperature
REG_MODE      = 0x006E  # 110 0=track 1=manual (rare legit write)
REG_SETPOINT  = 0x006F  # 111 commanded elevation setpoint — legit AND rogue write here

# =============================================================================
# minimal pcap / Ethernet / IPv4 / TCP framing (no external deps)
# =============================================================================
PCAP_GLOBAL = struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)  # LINKTYPE_ETHERNET


def ip_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f">{len(data)//2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def tcp_checksum(src_ip: bytes, dst_ip: bytes, tcp_seg: bytes) -> int:
    pseudo = src_ip + dst_ip + struct.pack(">BBH", 0, 6, len(tcp_seg))
    return ip_checksum(pseudo + tcp_seg)


def eth(dst_mac, src_mac, payload):
    return dst_mac + src_mac + b"\x08\x00" + payload


def ipv4(src_ip, dst_ip, payload, ident):
    src = bytes(int(x) for x in src_ip.split("."))
    dst = bytes(int(x) for x in dst_ip.split("."))
    total = 20 + len(payload)
    hdr = struct.pack(">BBHHHBBH", 0x45, 0, total, ident, 0x4000, 64, 6, 0) + src + dst
    hdr = hdr[:10] + struct.pack(">H", ip_checksum(hdr)) + hdr[12:]
    return hdr + payload, src, dst


def tcp(src_port, dst_port, seq, ack, payload, src_ip_b, dst_ip_b):
    off = (5 << 4)
    hdr = struct.pack(">HHIIBBHHH", src_port, dst_port, seq, ack, off, 0x18, 8192, 0, 0)  # PSH+ACK
    seg = hdr + payload
    cs = tcp_checksum(src_ip_b, dst_ip_b, seg)
    hdr = hdr[:16] + struct.pack(">H", cs) + hdr[18:]
    return hdr + payload


class TcpStreams:
    """Per-connection, per-direction TCP sequence/ack state.

    Each segment must carry a sequence number that advances by the bytes already
    sent on that half of the connection; otherwise every data segment reuses seq 0
    and Wireshark (with the default "Analyze TCP sequence numbers") flags all but
    the first as retransmissions of the first and refuses to dissect them as Modbus.
    The ack is the peer's current next-send seq, i.e. everything received so far.
    """
    def __init__(self, rng):
        self._rng = rng
        self._next = {}  # (src_ip, src_port, dst_ip, dst_port) -> next seq for that direction

    def _isn(self):
        return self._rng.randint(0x10000, 0xFFFFFFFF)

    def segment(self, src_ip, src_port, dst_ip, dst_port, paylen):
        fwd = (src_ip, src_port, dst_ip, dst_port)
        rev = (dst_ip, dst_port, src_ip, src_port)
        if fwd not in self._next:
            self._next[fwd] = self._isn()
        if rev not in self._next:
            self._next[rev] = self._isn()
        seq = self._next[fwd]
        ack = self._next[rev]  # next byte expected from the peer
        self._next[fwd] = (seq + paylen) & 0xFFFFFFFF
        return seq, ack


class Tid:
    def __init__(self): self.v = 0
    def next(self):
        self.v = (self.v + 1) & 0xFFFF
        return self.v


# =============================================================================
# Modbus/TCP PDUs
# =============================================================================
def mbap(tid, unit, pdu):
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu


def read_holding(tid, unit, start, count):
    return mbap(tid, unit, struct.pack(">BHH", 0x03, start, count))


def read_holding_resp(tid, unit, values):
    body = struct.pack(">BB", 0x03, len(values) * 2) + b"".join(struct.pack(">H", v) for v in values)
    return mbap(tid, unit, body)


def write_single(tid, unit, reg, value):
    return mbap(tid, unit, struct.pack(">BHH", 0x06, reg, value & 0xFFFF))  # req and resp are identical


# =============================================================================
# capture assembly
# =============================================================================
def build(seed):
    import random
    rng = random.Random(seed)
    # Independent RNG for TCP ISNs so adding sequence numbers doesn't perturb the
    # capture's own RNG stream (traffic pattern/timings stay as before — only the
    # TCP seq/ack fields change versus the seq-0 bug).
    streams = TcpStreams(random.Random(seed + 0xC0FFEE))
    packets = []          # (ts_float, frame)
    ident = [0x1000]
    t = [1_730_000_000.0]

    def emit(src, dst, payload):
        ident[0] = (ident[0] + 1) & 0xFFFF
        src_ip_b = bytes(int(x) for x in src["ip"].split("."))
        dst_ip_b = bytes(int(x) for x in dst["ip"].split("."))
        seq, ack = streams.segment(src["ip"], src["port"], dst["ip"], dst["port"], len(payload))
        seg = tcp(src["port"], dst["port"], seq, ack, payload, src_ip_b, dst_ip_b)
        ip_pkt, _, _ = ipv4(src["ip"], dst["ip"], seg, ident[0])
        frame = eth(dst["mac"], src["mac"], ip_pkt)
        t[0] += rng.uniform(0.001, 0.02)
        packets.append((t[0], frame))

    hmi_tid, hist_tid, eng_tid, rogue_tid = Tid(), Tid(), Tid(), Tid()
    unit = 1

    az, el, power, temp = 178.0, 41.0, 812.0, 47.0
    setpoint = 41

    total = 6000
    flag_bytes = FLAG.encode()
    # scatter rogue writes across the middle of the timeline
    rogue_slots = sorted(rng.sample(range(300, total - 100), len(flag_bytes)))
    slot_to_idx = {s: i for i, s in enumerate(rogue_slots)}

    for i in range(total):
        # HMI polls the two pointing registers
        tid = hmi_tid.next()
        emit(HMI, CTRL, read_holding(tid, unit, REG_AZIMUTH, 2))
        az = (az + rng.uniform(0.01, 0.05)) % 360
        el = max(0.0, min(90.0, el + rng.uniform(-0.03, 0.03)))
        emit(CTRL, HMI, read_holding_resp(tid, unit, [int(az * 10) & 0xFFFF, int(el * 10) & 0xFFFF]))

        # historian polls a wider block (adds volume + more visible registers)
        if i % 2 == 0:
            tid = hist_tid.next()
            emit(HIST, CTRL, read_holding(tid, unit, REG_AZIMUTH, 4))
            power = max(0.0, power + rng.uniform(-3, 3))
            temp = max(0.0, temp + rng.uniform(-0.2, 0.2))
            emit(CTRL, HIST, read_holding_resp(
                tid, unit,
                [int(az * 10) & 0xFFFF, int(el * 10) & 0xFFFF, int(power) & 0xFFFF, int(temp * 10) & 0xFFFF]))

        # legitimate engineering setpoint write (real traffic, small in-range value)
        if rng.random() < 0.04:
            setpoint = max(20, min(70, setpoint + rng.choice([-1, 1])))
            tid = eng_tid.next()
            emit(ENGWS, CTRL, write_single(tid, unit, REG_SETPOINT, setpoint))
            emit(CTRL, ENGWS, write_single(tid, unit, REG_SETPOINT, setpoint))
            # occasional legit mode toggle
            if rng.random() < 0.15:
                tid = eng_tid.next()
                emit(ENGWS, CTRL, write_single(tid, unit, REG_MODE, rng.choice([0, 1])))
                emit(CTRL, ENGWS, write_single(tid, unit, REG_MODE, 0))

        # rogue write: same IP as ENGWS, different MAC, same SETPOINT register,
        # value = one raw flag byte (overlaps the legit value range, so only the
        # MAC separates them)
        if i in slot_to_idx:
            ch = flag_bytes[slot_to_idx[i]]
            tid = rogue_tid.next()
            emit(ROGUE, CTRL, write_single(tid, unit, REG_SETPOINT, ch))
            emit(CTRL, ROGUE, write_single(tid, unit, REG_SETPOINT, ch))

    packets.sort(key=lambda p: p[0])
    return packets


def write_pcap(path, packets):
    with open(path, "wb") as f:
        f.write(PCAP_GLOBAL)
        for ts, frame in packets:
            sec = int(ts)
            usec = int((ts - sec) * 1_000_000)
            f.write(struct.pack("<IIII", sec, usec, len(frame), len(frame)))
            f.write(frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1106)
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.normpath(os.path.join(here, "..", "dist", "array_ctrl.pcap"))
    ap.add_argument("--out", default=default_out)
    args = ap.parse_args()
    packets = build(args.seed)
    write_pcap(args.out, packets)
    print(f"wrote {args.out}: {len(packets)} packets, {os.path.getsize(args.out)} bytes")


if __name__ == "__main__":
    main()
