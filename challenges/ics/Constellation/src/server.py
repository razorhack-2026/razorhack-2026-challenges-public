#!/usr/bin/env python3
"""
Constellation — Modbus TCP challenge server.

Register map (holding registers, read with function code 0x03):

  Address 1          : total number of coordinate points (N)
  Address 2 + i*3   : X of point i   (integer, 0-10000)
  Address 3 + i*3   : Y of point i   (integer, 0-10000)
  Address 4 + i*3   : pen of point i (0 = move, 1 = draw line from previous point)

Read all N points, then plot them in order:
  - pen=0  →  lift pen, move to (X, Y) without drawing
  - pen=1  →  draw a line from the previous point to (X, Y)

The resulting plot reveals the flag.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from pymodbus.simulator import DataType, SimData, SimDevice
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


def build_registers(coordinates_file: str) -> list[int]:
    path = Path(coordinates_file)
    if not path.exists():
        log.error("Coordinates file not found: %s", coordinates_file)
        log.error("Run  gen_coords.py \"CTF{...}\"  first to generate it.")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    count: int = data['count']
    regs: list[int] = [count]
    for p in data['points']:
        regs += [p['x'], p['y'], p['pen']]

    return regs


async def run_server(
    host: str = '0.0.0.0',
    port: int = 5020,
    coordinates_file: str = 'coordinates.json',
) -> None:
    regs = build_registers(coordinates_file)
    n_points = regs[0]

    sim_data = SimData(address=1, values=regs, datatype=DataType.REGISTERS)
    device = SimDevice(id=1, simdata=sim_data)

    log.info("Loaded %d coordinate points (%d registers total)", n_points, len(regs))
    log.info("Modbus TCP server listening on %s:%d", host, port)
    log.info("Register 1 = %d (point count)", n_points)
    log.info("Each point: 3 consecutive registers — X, Y, pen")
    await StartAsyncTcpServer(context=device, address=(host, port))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Constellation Modbus CTF server')
    parser.add_argument('--host', default='0.0.0.0', help='Bind address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5020, help='TCP port (default: 5020; use 502 in Docker)')
    parser.add_argument('--coords', default='coordinates.json', help='Path to coordinates.json')
    args = parser.parse_args()

    asyncio.run(run_server(host=args.host, port=args.port, coordinates_file=args.coords))
