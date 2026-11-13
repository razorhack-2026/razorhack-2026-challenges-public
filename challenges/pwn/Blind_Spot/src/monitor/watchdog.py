import logging
import socket
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

CONTROLLER_HOST = "10.13.37.10"
CONTROLLER_PORT = 502
UNIT_ID = 0x01

VALVE_REG = 0
FLOW_REG = 1
LOCKDOWN_REG = 50

SAFE_VALVE_MAX = 40
SAFE_FLOW_MAX = 500
LOCKDOWN_CODE = 0x00F0

POLL_INTERVAL_SECONDS = 2
CONNECT_TIMEOUT_SECONDS = 3

# Reported over mgmt_net every cycle — a private link the field segment
# doesn't have visibility into. This is our real, unspoofable report of what
# we actually saw; the plant_net lockdown write below is just the in-band
# emergency-reset action and isn't trusted on its own.
HEARTBEAT_HOST = "10.13.38.10"
HEARTBEAT_PORT = 9999


def report_heartbeat(safe: bool):
    try:
        with socket.create_connection((HEARTBEAT_HOST, HEARTBEAT_PORT), timeout=2) as s:
            s.sendall((b"SAFE\n" if safe else b"ALARM\n"))
    except OSError as exc:
        log.error("could not reach mgmt heartbeat link: %s", exc)


def poll_once():
    """Opens a fresh connection every cycle, like a real field watchdog would.
    Any read failure (dropped/blocked traffic) is treated as a fault, same as
    an out-of-range reading — going dark is exactly as suspicious as going bad."""
    client = ModbusTcpClient(host=CONTROLLER_HOST, port=CONTROLLER_PORT, timeout=CONNECT_TIMEOUT_SECONDS)
    try:
        if not client.connect():
            log.warning("cannot reach coolant loop controller — treating as fault")
            report_heartbeat(safe=False)
            trigger_lockdown()
            return

        rr = client.read_holding_registers(address=VALVE_REG, count=2, slave=UNIT_ID)
        if rr.isError():
            log.warning("read error from controller — treating as fault: %s", rr)
            report_heartbeat(safe=False)
            trigger_lockdown()
            return

        valve, flow = rr.registers
        if valve > SAFE_VALVE_MAX or flow > SAFE_FLOW_MAX:
            log.warning("OUT OF RANGE — valve=%d%% flow=%dL/s", valve, flow)
            report_heartbeat(safe=False)
            trigger_lockdown()
        else:
            log.info("nominal — valve=%d%% flow=%dL/s", valve, flow)
            report_heartbeat(safe=True)
    except ModbusException as exc:
        log.warning("modbus exception during poll — treating as fault: %s", exc)
        report_heartbeat(safe=False)
        trigger_lockdown()
    finally:
        client.close()


def trigger_lockdown():
    client = ModbusTcpClient(host=CONTROLLER_HOST, port=CONTROLLER_PORT, timeout=CONNECT_TIMEOUT_SECONDS)
    try:
        if client.connect():
            client.write_register(address=LOCKDOWN_REG, value=LOCKDOWN_CODE, slave=UNIT_ID)
            log.warning("lockdown command sent")
        else:
            log.error("could not send lockdown — controller unreachable")
    except ModbusException as exc:
        log.error("lockdown command failed: %s", exc)
    finally:
        client.close()


def run():
    log.info("watchdog online — polling %s:%d every %ds", CONTROLLER_HOST, CONTROLLER_PORT, POLL_INTERVAL_SECONDS)
    while True:
        poll_once()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
