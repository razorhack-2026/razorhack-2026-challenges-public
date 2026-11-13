#!/usr/bin/env python3
"""Listens on a monitor-mode interface (same phy as the real AP) for a
Probe Request carrying a specific vendor-specific information element
(802.11 element ID 221: OUI + OUI-type + payload). If the payload matches
the configured override key exactly, disables the AP's BSS via hostapd_cli.
"""

import os
import subprocess

from scapy.all import sniff
from scapy.layers.dot11 import Dot11, Dot11Elt, Dot11ProbeReq

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_IFACE = "wlan0-mon"
HOSTAPD_ODINS_IFACE = "wlan0"

# Vendor-specific IE: element ID 221, payload = OUI (3 bytes) + OUI-type (1
# byte) + the override key.
VENDOR_OUI = b"\x52\x5a\x52"  # RZR
VENDOR_OUI_TYPE = 0x01

OVERRIDE_KEY = "ODN-CLOS-EYES".encode()
EXPECTED_PAYLOAD = VENDOR_OUI + bytes([VENDOR_OUI_TYPE]) + OVERRIDE_KEY

def _disable_ap():
    subprocess.run(
        ["hostapd_cli", "-i", HOSTAPD_ODINS_IFACE, "disable"],
        capture_output=True, timeout=5,
    )

def _handle_frame(pkt):
    if not (pkt.haslayer(Dot11) and pkt.haslayer(Dot11ProbeReq)):
        return
    elt = pkt.getlayer(Dot11Elt)
    while elt:
        if elt.ID == 221 and bytes(elt.info) == EXPECTED_PAYLOAD:
            print("[+] Valid override signal received - disabling wlan0")
            _disable_ap()
            return
        elt = elt.payload.getlayer(Dot11Elt)


if __name__ == "__main__":
    print(f"[+] Listening for override signal on {MONITOR_IFACE}")
    sniff(iface=MONITOR_IFACE, prn=_handle_frame, store=False)
