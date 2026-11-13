#!/usr/bin/env python3
"""
Constellation — CTF solve script.

Connect to the Modbus TCP server, read the coordinate registers, and plot
the result to reveal the flag.

Usage: python solve.py <host> [port]
       python solve.py 10.0.0.1
       python solve.py 10.0.0.1 5020
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from pymodbus.client import ModbusTcpClient

FLAG_PNG_PATH = Path(__file__).resolve().parent / 'flag.png'


def read_points(host: str, port: int) -> list[tuple[int, int, int]]:
    client = ModbusTcpClient(host, port=port)
    if not client.connect():
        print(f"[-] Could not connect to {host}:{port}")
        sys.exit(1)

    # Register 1 holds the total number of points
    result = client.read_holding_registers(1, count=1)
    if result.isError():
        print("[-] Failed to read register 1")
        sys.exit(1)

    n = result.registers[0]
    print(f"[+] Connected to {host}:{port}")
    print(f"[+] {n} coordinate points to read ({n * 3} registers)")

    # Each point occupies 3 consecutive registers: X, Y, pen starting at address 2
    # Read in batches to stay under the 125-register Modbus limit
    points: list[tuple[int, int, int]] = []
    batch = 120
    for offset in range(0, n * 3, batch):
        count = min(batch, n * 3 - offset)
        result = client.read_holding_registers(2 + offset, count=count)
        if result.isError():
            print(f"[-] Failed to read registers at offset {offset}")
            sys.exit(1)
        regs = result.registers
        for i in range(0, len(regs) - 2, 3):
            points.append((regs[i], regs[i + 1], regs[i + 2]))

    client.close()
    print(f"[+] Read {len(points)} points")
    return points


def plot_flag(points: list[tuple[int, int, int]]) -> None:
    fig, ax = plt.subplots(figsize=(14, 5), facecolor='#05050f')
    ax.set_facecolor('#05050f')
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Constellation', color='#c8d8ff', fontsize=14, pad=10)

    prev: tuple[int, int] | None = None
    for x, y, pen in points:
        if pen == 1 and prev is not None:
            ax.plot([prev[0], x], [prev[1], y], color='#c8d8ff', lw=1.4, alpha=0.9)
        prev = (x, y)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.scatter(xs, ys, c='#00e5ff', s=5, zorder=5, alpha=0.75)

    plt.tight_layout(pad=0.5)
    plt.savefig(FLAG_PNG_PATH, dpi=150, bbox_inches='tight', facecolor='#05050f')
    print(f"[+] Flag plot saved -> {FLAG_PNG_PATH}")
    plt.show()


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5020
    points = read_points(host, port)
    plot_flag(points)
