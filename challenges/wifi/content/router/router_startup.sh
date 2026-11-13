#!/bin/bash
#
# Router/AP bring-up: the real ODINS_EYES AP (wlan0), a monitor-mode
# interface on the same phy for the override-signal listener, and the
# listener itself (content/router/passkey_listener.py).

set -e

echo "[+] Waiting for wlan0..."
while ! ip link show wlan0 >/dev/null 2>&1; do
    sleep 0.2
done
echo "[+] wlan0 detected"
ip link set wlan0 up

mkdir -p /var/run/hostapd

echo "[+] Starting hostapd (ODINS_EYES)"
hostapd -B /etc/hostapd/odins-eyes.conf
ip addr add 10.13.0.1/24 dev wlan0

echo "[+] Adding monitor interface on the same phy"
iw dev wlan0 interface add wlan0-mon type monitor
ip link set wlan0-mon up

echo "[+] Starting override-signal listener"
cd /opt/router
exec python3 passkey_listener.py
