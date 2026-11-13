#!/usr/bin/env python3
# BUILDER (src/, GM-only) — generates a realistic S7comm factory capture.
# Encodes write values with the SHIPPED tool's keystream so ciphertext in
# dist/ is exactly invertible from dist/interceptor.py. Holds key + flag.
import struct, sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dist"))
from interceptor import encode_value
from scapy.all import Ether, IP, TCP, ARP, Raw, PcapWriter

random.seed(1337)                                   # reproducible build
KEY  = bytes.fromhex("9c1f4ab7d0e35286a4f7c9130b6e57d2")
FLAG = "flag{s7comm_write_var_is_a_trust_boundary}"

WS   = ("192.168.95.10", "e4:90:69:0a:11:02")       # engineering workstation (TIA Portal)
PLC  = ("192.168.95.2",  "28:63:36:8f:5c:d1")       # S7-1200 extraction PLC
HIST = ("192.168.95.20", "00:1b:1b:44:9a:07")       # SCADA historian (background poller)
GW   = ("192.168.95.1",  "b4:fb:e4:0d:22:9c")

# ---------------- S7comm / COTP / TPKT byte builders ----------------
def tpkt(cotp_plus): 
    n = 4 + len(cotp_plus); return bytes([0x03,0x00,(n>>8)&0xff,n&0xff]) + cotp_plus
def cotp_cr(src_ref):
    body = bytes([0xe0,0x00,0x00,(src_ref>>8)&0xff,src_ref&0xff,0x00,
                  0xc1,0x02,0x01,0x00, 0xc2,0x02,0x01,0x02, 0xc0,0x01,0x0a])
    return tpkt(bytes([len(body)])+body)
def cotp_cc(src_ref,dst_ref):
    body = bytes([0xd0,(dst_ref>>8)&0xff,dst_ref&0xff,(src_ref>>8)&0xff,src_ref&0xff,0x00,
                  0xc1,0x02,0x01,0x02, 0xc2,0x02,0x01,0x00, 0xc0,0x01,0x0a])
    return tpkt(bytes([len(body)])+body)
COTP_DT = bytes([0x02,0xf0,0x80])
def s7_job(pduref, param, data=b""):
    hdr = bytes([0x32,0x01,0x00,0x00,(pduref>>8)&0xff,pduref&0xff,
                 (len(param)>>8)&0xff,len(param)&0xff,(len(data)>>8)&0xff,len(data)&0xff])
    return tpkt(COTP_DT + hdr+param+data)
def s7_ack(pduref, param, data=b""):
    hdr = bytes([0x32,0x03,0x00,0x00,(pduref>>8)&0xff,pduref&0xff,
                 (len(param)>>8)&0xff,len(param)&0xff,(len(data)>>8)&0xff,len(data)&0xff,0x00,0x00])
    return tpkt(COTP_DT + hdr+param+data)
def item(db, start, ln):
    return bytes([0x12,0x0a,0x10,0x02,(ln>>8)&0xff,ln&0xff,(db>>8)&0xff,db&0xff,0x84,
                  (start>>16)&0xff,(start>>8)&0xff,start&0xff])
def setup_param(): return bytes([0xf0,0x00,0x00,0x01,0x00,0x01,0x01,0xe0])
def read_req(pduref, db, start, ln):
    return s7_job(pduref, bytes([0x04,0x01])+item(db,start,ln))
def read_ack(pduref, value):
    ln=len(value); data=bytes([0xff,0x04,(ln*8>>8)&0xff,(ln*8)&0xff])+value
    if ln%2: data+=b'\x00'
    return s7_ack(pduref, bytes([0x04,0x01]), data)
def write_req(pduref, db, start, value):
    ln=len(value); data=bytes([0x00,0x04,(ln*8>>8)&0xff,(ln*8)&0xff])+value
    if ln%2: data+=b'\x00'
    return s7_job(pduref, bytes([0x05,0x01])+item(db,start,ln), data)
def write_ack(pduref):
    return s7_ack(pduref, bytes([0x05,0x01]), bytes([0xff]))

# ---------------- TCP session bookkeeping ----------------
class Conn:
    def __init__(self, cli, srv, sport):
        self.cli, self.srv, self.sport = cli, srv, sport
        self.cseq=random.randint(1,2**31-1); self.sseq=random.randint(1,2**31-1)
    def _p(self, src, dst, flags, seq, ack, pl=b""):
        sp = self.sport if src is self.cli else 102
        dp = 102 if src is self.cli else self.sport
        pk = Ether(src=src[1],dst=dst[1])/IP(src=src[0],dst=dst[0])/TCP(sport=sp,dport=dp,flags=flags,seq=seq,ack=ack,window=8192)
        return pk/Raw(load=pl) if pl else pk
    def hs(self, emit):
        emit(self._p(self.cli,self.srv,"S",self.cseq,0)); self.cseq+=1
        emit(self._p(self.srv,self.cli,"SA",self.sseq,self.cseq)); self.sseq+=1
        emit(self._p(self.cli,self.srv,"A",self.cseq,self.sseq))
    def c2s(self, pl, emit, gap=None):
        emit(self._p(self.cli,self.srv,"PA",self.cseq,self.sseq,pl), gap); self.cseq+=len(pl)
    def s2c(self, pl, emit, gap=None):
        emit(self._p(self.srv,self.cli,"PA",self.sseq,self.cseq,pl), gap); self.sseq+=len(pl)

# ---------------- capture clock ----------------
clock=[1717426800.0]   # 2024-06-03 ~13:00 UTC
wr = PcapWriter("dist/extraction_bus.pcap", sync=True)
def emit(pk, gap=None):
    if gap is None: gap=random.uniform(0.0004,0.0018)
    clock[0]+=gap; pk.time=clock[0]; wr.write(pk)

def arp_noise():
    who=Ether(src=GW[1],dst="ff:ff:ff:ff:ff:ff")/ARP(op=1,psrc=GW[0],pdst=random.choice([WS,PLC,HIST])[0],hwsrc=GW[1])
    emit(who, gap=random.uniform(0.02,0.09))

# ---------------- telemetry (plaintext reads) — fluctuating, NOT setpoints ----------------
def telemetry():
    return struct.pack(">8I", random.randint(2960,3040), random.randint(115,122),
                       random.randint(44,50), random.randint(10,13),
                       random.randint(0,3), random.randint(870,910),
                       random.randint(76,82), 0xA5A5)

# ---------------- known-plaintext operator setpoint pushes (DB1) ----------------
def profile(rate,pres,temp,ramp,bias,margin,duty,ilock):
    return struct.pack(">8I",rate,pres,temp,ramp,bias,margin,duty,ilock)
LEGIT = [
    (0x0101, profile(3000,118,47,12,0,900,80,0xA5A5)),
    (0x0102, profile(3050,120,48,12,0,900,80,0xA5A5)),
    (0x0103, profile(2980,117,46,11,0,880,78,0xA5A5)),
]
COVERT_PDUREF = 0x07FE
directive = (b"OVERRIDE ICARUS/extraction DB1.rate=8200 bias=0x5f "
             b"auth=Dr.Rootkit consent=none :: " + FLAG.encode() + b" ::")

# ---------------- build the session ----------------
ws = Conn(WS, PLC, 51713); hist = Conn(HIST, PLC, 49408)
ws.hs(emit); ws.c2s(cotp_cr(0x0001),emit); ws.s2c(cotp_cc(0x0001,0x0102),emit)
ws.c2s(s7_job(0x0000,setup_param()),emit); ws.s2c(s7_ack(0x0000,setup_param()),emit)
hist.hs(emit); hist.c2s(cotp_cr(0x0002),emit); hist.s2c(cotp_cc(0x0002,0x0103),emit)
hist.c2s(s7_job(0x0000,setup_param()),emit); hist.s2c(s7_ack(0x0000,setup_param()),emit)

# schedule the 4 writes at chosen poll-cycle indices, buried in the read stream
TOTAL=520
writes = dict(zip(sorted(random.sample(range(60, TOTAL-60), 4)),
                  LEGIT + [(COVERT_PDUREF, None)]))
rp = 0x1000       # rolling read pdu-ref
for i in range(TOTAL):
    # WS cyclic read of live telemetry (DB2), request + response
    rp = (rp+1) & 0xFFFF
    ws.c2s(read_req(rp,2,0,32),emit, gap=random.uniform(0.18,0.32))
    ws.s2c(read_ack(rp,telemetry()),emit, gap=random.uniform(0.001,0.004))
    # historian polls less often
    if i % 5 == 0:
        rp=(rp+1)&0xFFFF
        hist.c2s(read_req(rp,2,0,32),emit, gap=random.uniform(0.01,0.05))
        hist.s2c(read_ack(rp,telemetry()),emit, gap=random.uniform(0.001,0.004))
    if random.random()<0.03: arp_noise()
    if i in writes:
        pduref, payload = writes[i]
        if payload is None:                       # covert DB7 directive
            ct=encode_value(KEY,COVERT_PDUREF,directive)
            ws.c2s(write_req(COVERT_PDUREF,7,0,ct),emit, gap=random.uniform(0.05,0.12)); ws.s2c(write_ack(COVERT_PDUREF),emit, gap=random.uniform(0.002,0.006))
        else:                                     # legit DB1 setpoint push (encoded)
            ct=encode_value(KEY,pduref,payload)
            ws.c2s(write_req(pduref,1,0,ct),emit, gap=random.uniform(0.05,0.12)); ws.s2c(write_ack(pduref),emit, gap=random.uniform(0.002,0.006))
wr.close()

# console log: only the operator-sanctioned DB1 pushes (known plaintext)
with open("dist/workstation_console.log","w") as f:
    f.write("# ICARUS engineering workstation — extraction console audit (operator-sanctioned writes)\n")
    f.write("# Each line = one DB1 profile push. Fields are the DB1 record, in order.\n")
    f.write("# extraction_rate core_pressure coolant_temp ramp_limit harmonic_bias field_margin duty_cycle interlock_word\n")
    names=["extraction_rate","core_pressure","coolant_temp","ramp_limit",
           "harmonic_bias","field_margin","duty_cycle","interlock_word"]
    for pduref,rec in LEGIT:
        vals=struct.unpack(">8I",rec)
        f.write(f"[pdu 0x{pduref:04x}] WriteVar DB1 <- "+" ".join(f"{n}={v}" for n,v in zip(names,vals))+"\n")
    f.write("# (no console entry exists for the DB7 write seen on the bus)\n")

import glob
print("wrote dist/extraction_bus.pcap")
