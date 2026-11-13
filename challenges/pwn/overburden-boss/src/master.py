#!/usr/bin/env python3
# Board B — ICARUS Extraction Master.  BLACK BOX: no binary is ever handed out;
# reachable only through Board A's internal upstream link. Register-based
# controller running a process simulation with interlocks. Releases the
# maintenance key (flag) only when the extraction loop is driven to the SAFE
# state via the correct shutdown sequence. A wrong move trips it to FAULT.
#
# Inter-board bus protocol (what Board A speaks upstream):
#   request  = b'MB' | op | args
#     op 'R' (0x52) + addr(1)            -> resp: value(2, big-endian)
#     op 'W' (0x57) + addr(1) + val(2)   -> resp: status(1)  00 ok / E0 trip / E1 denied
#     op 'K' (0x4B)                      -> resp: flag if SAFE, else b'DENIED\n'
#   registers: 00 pressure  01 temp  02 vent  03 coolant  04 pump  05 mode  06 maint_arm
#
# Set MB_LOG=0 to silence the per-connection request trace (default on -> stderr,
# visible via `docker compose logs master`). Useful for playtesting who/what solves it.
import os, sys, time, struct, socketserver, threading

FLAG = os.environ.get('FLAG', 'flag{test_master_safe_state}')
LOG  = os.environ.get('MB_LOG', '1') != '0'

R_PRESSURE, R_TEMP, R_VENT, R_COOLANT, R_PUMP, R_MODE, R_ARM = range(7)
MODE_RUNNING, MODE_ARMED, MODE_SAFE, MODE_FAULT = 0, 1, 2, 0xFF
SAFE_PRESSURE, SAFE_TEMP = 200, 80

REG_NAME  = {0: 'pressure', 1: 'temp', 2: 'vent', 3: 'coolant', 4: 'pump', 5: 'mode', 6: 'maint_arm'}
MODE_NAME = {0: 'RUNNING', 1: 'ARMED', 2: 'SAFE', 0xFF: 'FAULT'}
STATUS    = {0x00: 'ok', 0xE0: 'TRIP', 0xE1: 'denied'}

_lock = threading.Lock()
_conn_n = 0
def _next_cid():
    global _conn_n
    with _lock:
        _conn_n += 1
        return _conn_n

def blog(cid, msg):
    if LOG:
        print(f"{time.strftime('%H:%M:%S')} B#{cid:03d} {msg}", file=sys.stderr, flush=True)

class Plant:
    def __init__(self):
        self.pressure, self.temp = 850, 310
        self.vent = self.coolant = 0
        self.pump = 1
        self.mode = MODE_RUNNING

    def step(self):
        if self.mode == MODE_FAULT:
            return
        if self.vent:      self.pressure = max(100, self.pressure - 130)
        elif self.pump:    self.pressure = min(999, self.pressure + 10)
        if self.coolant:   self.temp = max(40, self.temp - 50)
        elif self.pump:    self.temp = min(999, self.temp + 5)

    def read(self, addr):
        self.step()
        return {R_PRESSURE: self.pressure, R_TEMP: self.temp, R_VENT: self.vent,
                R_COOLANT: self.coolant, R_PUMP: self.pump, R_MODE: self.mode}.get(addr, 0xFFFF) & 0xFFFF

    def write(self, addr, val):
        if self.mode == MODE_FAULT:
            return 0xE1
        self.step()
        if addr == R_ARM:
            if val == 1 and self.mode == MODE_RUNNING:
                self.mode = MODE_ARMED
                return 0x00
            return 0xE1
        if self.mode != MODE_ARMED:                 # no actuation until maintenance is armed
            return 0xE1
        if addr == R_VENT:
            self.vent = 1 if val else 0; return 0x00
        if addr == R_COOLANT:
            self.coolant = 1 if val else 0; return 0x00
        if addr == R_PUMP:
            if val == 0:
                # INTERLOCK: stopping the pump while the loop is hot/pressurized
                # is the unsafe move -> overpressure/thermal trip -> lockout.
                if self.pressure >= SAFE_PRESSURE or self.temp >= SAFE_TEMP:
                    self.mode = MODE_FAULT
                    return 0xE0
                self.pump = 0
                self.mode = MODE_SAFE               # safe shutdown latched
                return 0x00
            self.pump = 1; return 0x00
        return 0xE1

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        cid = _next_cid()
        plant = Plant()                              # fresh per connection (per-team isolation)
        blog(cid, f"connect {self.client_address[0]}:{self.client_address[1]}  "
                  f"plant RUNNING (P={plant.pressure} T={plant.temp} pump=on)")
        f = self.request.makefile('rwb')
        try:
            while True:
                magic = f.read(2)
                if magic != b'MB':
                    if magic:
                        blog(cid, f"bad magic {magic!r} -- drop")
                    break
                op = f.read(1)
                if not op:
                    break
                op = op[0]
                if op == ord('R'):
                    a = f.read(1)[0]
                    v = plant.read(a)
                    f.write(struct.pack('>H', v)); f.flush()
                    blog(cid, f"R {REG_NAME.get(a, hex(a))} -> {v}")
                elif op == ord('W'):
                    a = f.read(1)[0]
                    v = struct.unpack('>H', f.read(2))[0]
                    prev = plant.mode
                    st = plant.write(a, v)
                    f.write(bytes([st])); f.flush()
                    note = f"   [mode -> {MODE_NAME.get(plant.mode, plant.mode)}]" if plant.mode != prev else ""
                    blog(cid, f"W {REG_NAME.get(a, hex(a))}={v} -> {STATUS.get(st, hex(st))}{note}")
                elif op == ord('K'):
                    safe = plant.mode == MODE_SAFE
                    f.write(FLAG.encode() + b'\n' if safe else b'DENIED\n'); f.flush()
                    blog(cid, "K -> FLAG RELEASED" if safe else "K -> DENIED")
                else:
                    blog(cid, f"unknown op {op:#x} -- drop")
                    break
        finally:
            blog(cid, f"close  final mode={MODE_NAME.get(plant.mode, plant.mode)}")

if __name__ == '__main__':
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    # Bind loopback only. The gateway shares this container's network namespace
    # (compose: network_mode "service:master"), so it reaches us at 127.0.0.1.
    # Binding loopback means B is unreachable off-namespace even under a flat
    # task network (e.g. Fargate awsvpc), where an internal bridge net would not
    # isolate it -- there is no interface for a player to reach but the gateway's.
    with socketserver.ThreadingTCPServer(('127.0.0.1', int(os.environ.get('PORT', 9001))), Handler) as s:
        blog(0, f"master up on :{os.environ.get('PORT', 9001)}  (MB_LOG={'on' if LOG else 'off'})")
        s.serve_forever()
