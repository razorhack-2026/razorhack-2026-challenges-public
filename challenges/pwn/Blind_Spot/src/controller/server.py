import asyncio
import logging
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

FLAG              = "flag{the_monitor_saw_nothing}"
UNIT_ID           = 0x01

VALVE_REG         = 0        # valve_position (%),      safe <= SAFE_VALVE_MAX
FLOW_REG          = 1        # flow_rate (L/s),          safe <= SAFE_FLOW_MAX
LOCKDOWN_COUNT_REG = 2       # [R] how many times the watchdog has reset us
LOCKDOWN_REG      = 50       # [W] write LOCKDOWN_CODE here to force a safe reset
FLAG_REG_START    = 100      # [R] flag chars, unlocked once tamper goes undetected

SAFE_VALVE_MAX    = 40
SAFE_FLOW_MAX     = 500
SAFE_VALVE_DEFAULT = 15
SAFE_FLOW_DEFAULT  = 220

LOCKDOWN_CODE     = 0x00F0
GRACE_SECONDS     = 20        # how long tamper must go unnoticed before the flag unlocks

# Heartbeat: monitor reports its real verdict here every poll cycle, over
# mgmt_net — a private network the attacker has no interface on at all. This
# is what flag-unlock actually gates on. It is NOT the same thing as
# LOCKDOWN_REG above: that's a plant_net write (spoofable, and mostly here
# for in-band flavor/visibility), whereas this channel can't be blackholed
# or forged from the jump box, so a "just ARP-poison and drop everything"
# shortcut can't silence it the way it can silence the plant_net write.
HEARTBEAT_BIND_IP = "10.13.38.10"
HEARTBEAT_PORT    = 9999
HEARTBEAT_STALE_SECONDS = 5   # monitor polls every 2s; this allows for jitter


class CoolantLoopRegisters(ModbusSequentialDataBlock):
    """Holding registers for the habitat ring coolant loop controller.

    Register map (address, read/write):
      0    valve_position   [R/W]  0-100 %, safe at or below 40
      1    flow_rate        [R/W]  0-999 L/s, safe at or below 500
      2    lockdown_count   [R]    number of watchdog-forced resets
      50   LOCKDOWN (write) [W]    write 0x00F0 to force an emergency safe reset
      100  FLAG_0 (100+)    [R]    flag chars, unlocked once tamper survives
                                   unnoticed for GRACE_SECONDS
    """

    def __init__(self):
        values = [0] * 4096
        values[VALVE_REG] = SAFE_VALVE_DEFAULT
        values[FLOW_REG] = SAFE_FLOW_DEFAULT
        values[LOCKDOWN_COUNT_REG] = 0
        self._flag_unlocked = False
        self._unsafe_since = None
        self._last_heartbeat_time = None
        self._last_heartbeat_safe = False
        super().__init__(0x0000, values)

    def _is_unsafe(self):
        return (
            self.getValues(VALVE_REG, 1)[0] > SAFE_VALVE_MAX
            or self.getValues(FLOW_REG, 1)[0] > SAFE_FLOW_MAX
        )

    def _reset_to_safe(self):
        super().setValues(VALVE_REG, [SAFE_VALVE_DEFAULT])
        super().setValues(FLOW_REG, [SAFE_FLOW_DEFAULT])
        count = self.getValues(LOCKDOWN_COUNT_REG, 1)[0]
        super().setValues(LOCKDOWN_COUNT_REG, [(count + 1) & 0xFFFF])
        self._unsafe_since = None

    def setValues(self, address, values):
        if address == LOCKDOWN_REG and values and values[0] == LOCKDOWN_CODE:
            log.warning("WATCHDOG ALARM — forcing emergency safe reset")
            self._reset_to_safe()
            return

        if address == LOCKDOWN_COUNT_REG:
            return  # read-only telemetry; ignore external writes

        super().setValues(address, values)

        if address in (VALVE_REG, FLOW_REG) and not self._flag_unlocked:
            if self._is_unsafe():
                if self._unsafe_since is None:
                    self._unsafe_since = time.monotonic()
                    log.info("coolant loop drifted out of safe range")
            else:
                self._unsafe_since = None

    def record_heartbeat(self, safe: bool):
        self._last_heartbeat_time = time.monotonic()
        self._last_heartbeat_safe = safe

    def _watchdog_currently_pacified(self) -> bool:
        if self._last_heartbeat_time is None:
            return False
        if time.monotonic() - self._last_heartbeat_time > HEARTBEAT_STALE_SECONDS:
            return False   # heartbeat gone stale/dark — treat like detection
        return self._last_heartbeat_safe

    def tick(self):
        """Called once a second by the background loop to check for a sustained,
        undetected tamper. Real detection is gated on the mgmt_net heartbeat,
        not the plant_net lockdown write — the watchdog going dark (blackholed)
        is exactly as suspicious as it reporting an alarm."""
        if self._flag_unlocked or self._unsafe_since is None:
            return

        if not self._watchdog_currently_pacified():
            self._unsafe_since = None
            return

        if time.monotonic() - self._unsafe_since >= GRACE_SECONDS:
            self._flag_unlocked = True
            log.warning("tamper went unnoticed for %ds — unlocking flag registers %d+",
                        GRACE_SECONDS, FLAG_REG_START)
            for i, ch in enumerate(FLAG):
                super().setValues(FLAG_REG_START + i, [ord(ch)])
            super().setValues(FLAG_REG_START + len(FLAG), [0x0000])


async def background_ticker(holding: CoolantLoopRegisters):
    while True:
        await asyncio.sleep(1)
        holding.tick()


async def handle_heartbeat(holding: CoolantLoopRegisters, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        verdict = line.decode().strip().upper()
        holding.record_heartbeat(safe=(verdict == "SAFE"))
    except (asyncio.TimeoutError, UnicodeDecodeError):
        pass
    finally:
        writer.close()


async def run():
    holding = CoolantLoopRegisters()
    slave = ModbusSlaveContext(hr=holding, zero_mode=True)
    context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "RazorPower Co."
    identity.ProductCode = "CLC-9"
    identity.MajorMinorRevision = "v1.4.0"
    identity.ProductName = "Habitat Ring Coolant Loop Controller"
    identity.ModelName = "CLC-9"
    identity.UserApplicationName = "Coolant Loop Control"

    asyncio.ensure_future(background_ticker(holding))
    await asyncio.start_server(
        lambda r, w: handle_heartbeat(holding, r, w),
        host=HEARTBEAT_BIND_IP, port=HEARTBEAT_PORT,
    )
    log.info("Heartbeat listener bound to %s:%d (mgmt_net only)", HEARTBEAT_BIND_IP, HEARTBEAT_PORT)

    log.info("CLC-9 coolant loop controller listening on 0.0.0.0:502  (unit ID: 0x%02X)", UNIT_ID)
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=("0.0.0.0", 502),
    )


if __name__ == "__main__":
    asyncio.run(run())
