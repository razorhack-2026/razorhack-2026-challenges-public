#!/usr/bin/env python3
"""
IED-BKR-07 -- breaker bay controller.

Three jobs:
  1. Publish its own position-status GOOSE control block (`gcbPos`) --
     decoy traffic. A technician racks the breaker open/closed a few times
     during the maintenance window; these frames look like state changes
     too, but IED-BKR-07 doesn't trip *itself* off its own status echo.
  2. Listen on the wire for IED-PROT-03's trip control block (`gcbTrip`)
     and only act on a frame that is genuinely `test=False` -- per
     IEC 61850-8-1, a compliant subscriber must never act on a GOOSE
     message flagged as a test unless it is itself in test mode. Replaying
     any of the `test=True` rehearsal frames does nothing here.
  3. Expose breaker status over Modbus/TCP -- the same "SCADA view"
     pattern used elsewhere in this set -- and unlock the flag registers
     once the real trip lands.
"""

import asyncio
import logging
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, "/app/common")
import goose  # noqa: E402

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

IFACE = os.environ.get("IFACE", "eth0")
BROADCAST = b"\xff\xff\xff\xff\xff\xff"
ETHERTYPE_GOOSE = goose.ETHERTYPE_GOOSE

TRIP_GOCB_REF = "IED_PROT03LLN0$GO$gcbTrip"
POS_GOCB_REF = "IED_BKR07LLN0$GO$gcbPos"
POS_DATSET = "IED_BKR07LLN0$PosDataSet"
POS_GO_ID = "gcbPos"
APPID = 0x0002

FLAG = os.environ.get("FLAG", "flag{ghost_command_placeholder_flag}")
UNIT_ID = 0x01

POS_REG = 0          # [R] breaker position: 0=open, 1=closed
TRIPPED_REG = 1      # [R] 1 once a genuine trip has been accepted
FLAG_REG_START = 100  # [R] flag chars, unlocked on genuine trip


def get_mac(iface):
    with open(f"/sys/class/net/{iface}/address") as f:
        return bytes.fromhex(f.read().strip().replace(":", ""))


class BreakerRegisters(ModbusSequentialDataBlock):
    def __init__(self):
        values = [0] * 4096
        values[POS_REG] = 1  # starts closed
        values[TRIPPED_REG] = 0
        super().__init__(0x0000, values)
        self._tripped = False

    def set_position(self, closed: bool):
        super().setValues(POS_REG, [1 if closed else 0])

    def accept_genuine_trip(self):
        if self._tripped:
            return
        self._tripped = True
        super().setValues(POS_REG, [0])
        super().setValues(TRIPPED_REG, [1])
        log.warning("GENUINE trip accepted -- breaker OPEN, unlocking flag registers")
        for i, ch in enumerate(FLAG):
            super().setValues(FLAG_REG_START + i, [ord(ch)])
        super().setValues(FLAG_REG_START + len(FLAG), [0x0000])


def position_publisher(src_mac, registers):
    """Decoy traffic: IED-BKR-07 echoing its own breaker position."""
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_GOOSE))
    sock.bind((IFACE, ETHERTYPE_GOOSE))

    st_num = 1
    sq_num = 0
    closed = True

    def send(test, closed_val):
        nonlocal sq_num
        pdu = goose.build_goose_apdu(
            gocb_ref=POS_GOCB_REF, dat_set=POS_DATSET, go_id=POS_GO_ID,
            st_num=st_num, sq_num=sq_num, test=test, data_values=[closed_val],
            conf_rev=1,
        )
        frame = goose.build_goose_frame(BROADCAST, src_mac, APPID, pdu)
        sock.send(frame)
        print(f"[bkr-pos] stNum={st_num} sqNum={sq_num} test={test} closed={closed_val}", flush=True)

    def toggle():
        nonlocal st_num, sq_num, closed
        closed = not closed
        st_num += 1
        for sq in range(4):
            sq_num = sq
            send(True, closed)
            time.sleep(0.3)
        sq_num = 0

    # Manual rack-out/rack-in exercise, timed to overlap the prot rehearsal
    # window so the two decoy streams interleave in the capture.
    toggle_times = [12, 28, 55, 70]
    start = time.time()
    next_heartbeat = start + 4
    next_toggle_idx = 0

    while True:
        now = time.time() - start
        if next_toggle_idx < len(toggle_times) and now >= toggle_times[next_toggle_idx]:
            toggle()
            next_toggle_idx += 1
            next_heartbeat = time.time() + 4
        elif time.time() >= next_heartbeat:
            sq_num += 1
            send(True, closed)
            next_heartbeat = time.time() + 4
        time.sleep(0.1)


def trip_listener(registers):
    """Only reacts to a genuine (test=False) trip on the PROT control block."""
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_GOOSE))
    sock.bind((IFACE, ETHERTYPE_GOOSE))

    while True:
        raw = sock.recv(2048)
        frame = goose.parse_goose_frame(raw)
        if frame is None or frame.gocb_ref != TRIP_GOCB_REF:
            continue

        if frame.test:
            log.info("ignoring test-flagged trip frame (stNum=%d sqNum=%d) — not acting",
                      frame.st_num, frame.sq_num)
            continue

        if frame.data_values and frame.data_values[0] is True:
            registers.accept_genuine_trip()


async def run():
    src_mac = get_mac(IFACE)
    registers = BreakerRegisters()
    slave = ModbusSlaveContext(hr=registers, zero_mode=True)
    context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "RazerPowerCo"
    identity.ProductCode = "BKR-07"
    identity.MajorMinorRevision = "v2.1.0"
    identity.ProductName = "Docking Ring 3 Feeder Breaker Controller"
    identity.ModelName = "IED-BKR-07"
    identity.UserApplicationName = "Breaker Bay Control"

    threading.Thread(target=position_publisher, args=(src_mac, registers), daemon=True).start()
    threading.Thread(target=trip_listener, args=(registers,), daemon=True).start()

    log.info("IED-BKR-07 listening on 0.0.0.0:502 (unit ID 0x%02X)", UNIT_ID)
    await StartAsyncTcpServer(context=context, identity=identity, address=("0.0.0.0", 502))


if __name__ == "__main__":
    asyncio.run(run())
