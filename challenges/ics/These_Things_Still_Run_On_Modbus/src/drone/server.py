import asyncio
import logging
import os
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

FLAG             = "flag{d3t0n4t3_dm7}"
UNIT_ID          = 0x0A
DESTRUCT_REG     = 1337
DESTRUCT_CODE    = 0x4444
FLAG_REG_START   = 2000

# Brute-force guard on DESTRUCT_REG: the code is only 16 bits, so without
# this a script could just write all 65536 values to register 1337 and
# read register 2000 after each one, skipping the website/manual entirely.
# After a few wrong codes, lock the register out for a cooldown; this adds
# essentially no friction for someone who read the manual and writes the
# right code within their first couple of tries, but makes an exhaustive
# sweep take days instead of seconds.
DESTRUCT_MAX_ATTEMPTS  = 3
DESTRUCT_LOCKOUT_SECS  = 30

# The vendor URL FC43 hands back to whoever's fingerprinting the drone.
# Defaults to the docker-compose internal bridge address for local GM
# testing, where drone + website share one network. At the real venue,
# set VENDOR_URL to wherever the website is actually reachable from a
# participant (e.g. http://<challenge-host>:<mapped-port>) — the
# internal bridge IP is never routable from outside the container network.
VENDOR_URL       = os.environ.get("VENDOR_URL", "http://10.13.37.50")


class DroneHoldingRegisters(ModbusSequentialDataBlock):
    """Holding register block for the DM-7 mining drone.

    Register map (address, read/write):
      0x0000  ore_density_kg_m3       [R]   current ore density
      0x0001  thruster_temp_celsius   [R]   primary thruster temperature
      0x0002  battery_percent         [R]   battery state-of-charge
      0x0003  operational_status      [R]   0=IDLE 1=TRANSIT 2=DRILL 3=MINING 4=RTB
      0x0004  sector_id               [R]   current asteroid sector
      0x0005  fault_flags             [R]   bitmask of active faults
      0x0539  DESTRUCT_AUTH (1337)    [W]   write 0x4444 with unit 0x0A to arm EDP
      0x07D0  FLAG_0 (2000+)          [R]   flag chars, unlocked after EDP
    """

    def __init__(self):
        values = [0] * 4096
        values[0] = 0x0047   # ore_density:      71 kg/m³
        values[1] = 0x01F4   # thruster_temp:    500 °C
        values[2] = 0x0059   # battery:          89 %
        values[3] = 0x0003   # status:           MINING
        values[4] = 0x1A2B   # sector_id:        0x1A2B
        values[5] = 0x0000   # fault_flags:      none
        self._flag_unlocked = False
        self._fail_count = 0
        self._locked_until = 0.0
        super().__init__(0x0000, values)

    def setValues(self, address, values):
        if address == DESTRUCT_REG and values and not self._flag_unlocked:
            now = time.monotonic()
            if now < self._locked_until:
                log.warning(
                    "DESTRUCT_REG write dropped — locked out for another %.0fs",
                    self._locked_until - now,
                )
                return

            if values[0] == DESTRUCT_CODE:
                self._flag_unlocked = True
                log.warning("DESTRUCT SEQUENCE AUTHORIZED — writing flag to registers %d+", FLAG_REG_START)
                for i, ch in enumerate(FLAG):
                    super().setValues(FLAG_REG_START + i, [ord(ch)])
                super().setValues(FLAG_REG_START + len(FLAG), [0x0000])
            else:
                self._fail_count += 1
                if self._fail_count >= DESTRUCT_MAX_ATTEMPTS:
                    self._locked_until = now + DESTRUCT_LOCKOUT_SECS
                    self._fail_count = 0
                    log.warning(
                        "DESTRUCT_REG locked out for %ds after %d wrong codes",
                        DESTRUCT_LOCKOUT_SECS, DESTRUCT_MAX_ATTEMPTS,
                    )

        super().setValues(address, values)


async def run():
    holding = DroneHoldingRegisters()
    slave   = ModbusSlaveContext(hr=holding, zero_mode=True)
    context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName          = "AstraTech Industries"
    identity.ProductCode         = "DM-7"
    identity.MajorMinorRevision  = "v2.3.1"
    identity.VendorUrl           = VENDOR_URL
    identity.ProductName         = "AstraTech DM-7 Mining Drone"
    identity.ModelName           = "DM-7"
    identity.UserApplicationName = "Autonomous Mineral Extraction Unit"

    log.info("DM-7 Modbus server listening on 0.0.0.0:502  (unit ID: 0x%02X)", UNIT_ID)
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=("0.0.0.0", 502),
    )


if __name__ == "__main__":
    asyncio.run(run())
