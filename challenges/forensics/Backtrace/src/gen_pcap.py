#!/usr/bin/env python3
"""
Backtrace -- pcap generator.

Builds a synthetic packet capture of the ISV Kestrel's internal shipnet
during the shift in which the airlock-plc safety interlock was disabled.

Story or the capture, in order:

  1. Routine Modbus/TCP polling noise: eng-console <-> airlock-plc.
  2. The leak: voss-ws uploads a gzip-compressed config backup to the
     internal file server over plaintext FTP. The backup contains R. Voss's
     engineering-console credentials and the flag.
  3. More polling noise.
  4. The access: an unrecognized terminal (mtx-47) telnets into
     eng-console using voss's leaked credentials.
  5. The attack: eng-console (now attacker-controlled) sends a Modbus
     write disabling the airlock safety interlock coil.
  6. A little more polling noise showing the post-attack state.

Run:
    python gen_pcap.py [-o ../dist/kestrel_shipnet.pcap]
"""

import argparse
import gzip
import random
from datetime import datetime, timezone

from scapy.all import Ether, IP, TCP, Raw, wrpcap
from scapy.contrib.modbus import (
    ModbusADURequest,
    ModbusADUResponse,
    ModbusPDU01ReadCoilsRequest,
    ModbusPDU01ReadCoilsResponse,
    ModbusPDU03ReadHoldingRegistersRequest,
    ModbusPDU03ReadHoldingRegistersResponse,
    ModbusPDU05WriteSingleCoilRequest,
    ModbusPDU05WriteSingleCoilResponse,
)

random.seed(1337)

# ── Cast of hosts ────────────────────────────────────────────────────────────

ENG_CONSOLE = dict(ip="10.10.0.2",  mac="02:00:00:00:00:02")   # engineering console (telnet + modbus master)
FILE_SERVER = dict(ip="10.10.0.5",  mac="02:00:00:00:00:05")   # internal file server (ftp)
AIRLOCK_PLC = dict(ip="10.10.0.10", mac="02:00:00:00:00:0a")   # airlock safety PLC (modbus/tcp unit 1)
VOSS_WS     = dict(ip="10.10.0.15", mac="02:00:00:00:00:0f")   # R. Voss's assigned workstation
MTX_47      = dict(ip="10.10.0.47", mac="02:00:00:00:00:2f")   # unassigned maintenance terminal, Cargo Bay 2

FLAG = "flag{never_ftp_your_secrets_into_space}"

BACKUP_CONTENT = f"""\
# Kestrel Shipnet Engineering Backup
# tool: shipnet-backup v2.3 (gzip)
[engineering_console]
username=rvoss
password=Kestrel#Eng77
role=engineer
last_rotated=2024-05-02

# ops note: reminder ticket ENG-4471 closed
# recovery token: {FLAG}
""".encode()

BASE_TIME = datetime(2024, 6, 15, 2, 0, 0, tzinfo=timezone.utc).timestamp()


# ── TCP stream helper ────────────────────────────────────────────────────────

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


# ── Modbus polling noise ─────────────────────────────────────────────────────

def modbus_poll_round(t0, trans_id):
    """One console->plc polling cycle: read coils 0-1, then holding regs 0-2."""
    sess = TCPSession(ENG_CONSOLE, random.randint(50000, 60000), AIRLOCK_PLC, 502, t0)
    sess.handshake()

    req1 = bytes(ModbusADURequest(transId=trans_id, unitId=1) / ModbusPDU01ReadCoilsRequest(startAddr=0, quantity=2))
    sess.send(True, req1)
    resp1 = bytes(ModbusADUResponse(transId=trans_id, unitId=1) / ModbusPDU01ReadCoilsResponse(byteCount=1, coilStatus=0b00000001))
    sess.send(False, resp1)

    req2 = bytes(ModbusADURequest(transId=trans_id + 1, unitId=1) / ModbusPDU03ReadHoldingRegistersRequest(startAddr=0, quantity=3))
    sess.send(True, req2)
    pressure, temp, occupancy = 1013, 21, 0
    resp2 = bytes(
        ModbusADUResponse(transId=trans_id + 1, unitId=1)
        / ModbusPDU03ReadHoldingRegistersResponse(byteCount=6, registerVal=[pressure, temp, occupancy])
    )
    sess.send(False, resp2)

    sess.close()
    return sess.pkts, sess.t


def modbus_poll_round_breached(t0, trans_id):
    """Same as above but coil 0 (interlock) now reads disabled (0)."""
    sess = TCPSession(ENG_CONSOLE, random.randint(50000, 60000), AIRLOCK_PLC, 502, t0)
    sess.handshake()

    req1 = bytes(ModbusADURequest(transId=trans_id, unitId=1) / ModbusPDU01ReadCoilsRequest(startAddr=0, quantity=2))
    sess.send(True, req1)
    resp1 = bytes(ModbusADUResponse(transId=trans_id, unitId=1) / ModbusPDU01ReadCoilsResponse(byteCount=1, coilStatus=0b00000000))
    sess.send(False, resp1)

    sess.close()
    return sess.pkts, sess.t


# ── FTP leak session ─────────────────────────────────────────────────────────

def ftp_leak_session(t0):
    """Builds the FTP control + data streams with packets kept in true
    chronological order (the data channel opens and closes in the middle
    of the control-channel conversation)."""
    pkts = []
    ctrl = TCPSession(VOSS_WS, 51000, FILE_SERVER, 21, t0)

    def flush(sess):
        pkts.extend(sess.pkts)
        sess.pkts = []

    ctrl.handshake()
    flush(ctrl)

    def c2s(msg):
        ctrl.send(True, msg.encode())
        flush(ctrl)

    def s2c(msg):
        ctrl.send(False, msg.encode())
        flush(ctrl)

    s2c("220 shipnet-fs FTP backup service ready\r\n")
    c2s("USER rvoss\r\n")
    s2c("331 Password required for rvoss\r\n")
    c2s("PASS Kestrel#Eng77\r\n")
    s2c("230 User rvoss logged in\r\n")
    c2s("TYPE I\r\n")
    s2c("200 Type set to I\r\n")

    data_port = 51001
    s2c(f"227 Entering Passive Mode (10,10,0,5,{data_port // 256},{data_port % 256})\r\n")
    c2s("STOR eng_accounts.bak.gz\r\n")
    s2c("150 Opening BINARY mode data connection for eng_accounts.bak.gz\r\n")

    # data channel opens, transfers the gzipped backup, and closes here
    data = TCPSession(VOSS_WS, 51002, FILE_SERVER, data_port, ctrl.t + 0.05)
    data.handshake()
    flush(data)
    payload = gzip.compress(BACKUP_CONTENT)
    for i in range(0, len(payload), 512):
        data.send(True, payload[i:i + 512])
        flush(data)
    data.close()
    flush(data)

    ctrl.t = data.t + 0.05
    s2c("226 Transfer complete\r\n")
    c2s("QUIT\r\n")
    s2c("221 Goodbye\r\n")
    ctrl.close()
    flush(ctrl)

    return pkts, ctrl.t


# ── Telnet intrusion session ─────────────────────────────────────────────────

def telnet_intrusion_session(t0):
    sess = TCPSession(MTX_47, 43210, ENG_CONSOLE, 23, t0)
    sess.handshake()

    def s2c(msg):
        sess.send(False, msg.encode())

    def c2s(msg):
        sess.send(True, msg.encode())

    s2c("Kestrel Engineering Console\r\nlogin: ")
    c2s("rvoss\r\n")
    s2c("Password: ")
    c2s("Kestrel#Eng77\r\n")
    s2c("Login OK\r\nconsole> ")
    c2s("interlock airlock disable\r\n")
    s2c("WARNING: disabling safety interlock on airlock-plc (coil 0)\r\nconsole> ")

    sess.close()
    return sess.pkts, sess.t


# ── Assembly ──────────────────────────────────────────────────────────────────

def build_capture():
    pkts = []
    t = BASE_TIME
    trans_id = 1

    # 1. routine polling noise
    for _ in range(6):
        round_pkts, t = modbus_poll_round(t, trans_id)
        pkts += round_pkts
        trans_id += 2
        t += random.uniform(10, 20)

    # 2. the leak
    t += random.uniform(20, 40)
    leak_pkts, t = ftp_leak_session(t)
    pkts += leak_pkts

    # 3. more polling noise
    for _ in range(10):
        round_pkts, t = modbus_poll_round(t, trans_id)
        pkts += round_pkts
        trans_id += 2
        t += random.uniform(60, 180)

    # 4 + 5. the intrusion and the malicious write
    t += random.uniform(30, 60)
    intrusion_pkts, t = telnet_intrusion_session(t)
    pkts += intrusion_pkts

    t += random.uniform(2, 5)
    write_sess = TCPSession(ENG_CONSOLE, random.randint(50000, 60000), AIRLOCK_PLC, 502, t)
    write_sess.handshake()
    wreq = bytes(ModbusADURequest(transId=trans_id, unitId=1) / ModbusPDU05WriteSingleCoilRequest(outputAddr=0, outputValue=0x0000))
    write_sess.send(True, wreq)
    wresp = bytes(ModbusADUResponse(transId=trans_id, unitId=1) / ModbusPDU05WriteSingleCoilResponse(outputAddr=0, outputValue=0x0000))
    write_sess.send(False, wresp)
    write_sess.close()
    pkts += write_sess.pkts
    trans_id += 1
    t = write_sess.t

    # 6. post-attack polling, showing the interlock coil now reads disabled
    for _ in range(3):
        round_pkts, t = modbus_poll_round_breached(t, trans_id)
        pkts += round_pkts
        trans_id += 1
        t += random.uniform(10, 20)

    return pkts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../dist/kestrel_shipnet.pcap")
    args = ap.parse_args()

    pkts = build_capture()
    pkts.sort(key=lambda p: p.time)
    wrpcap(args.out, pkts)
    print(f"[+] wrote {len(pkts)} packets to {args.out}")
    print(f"[+] flag: {FLAG}")


if __name__ == "__main__":
    main()
