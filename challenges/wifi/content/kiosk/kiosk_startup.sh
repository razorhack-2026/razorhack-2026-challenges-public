#!/bin/bash

set -e

echo "[+] Waiting for wlan0..."

while ! ip link show wlan0 >/dev/null 2>&1; do
    sleep 0.2
done

echo "[+] wlan0 detected"

ip link set wlan0 up

echo "[+] Starting wpa_supplicant"

wpa_supplicant \
    -B \
    -i wlan0 \
    -c /etc/wpa_supplicant/client-bridged.conf

echo "[+] Waiting for Wi-Fi association..."

for i in {1..30}; do
    if iw dev wlan0 link | grep -q "Connected"; then
        echo "[+] Associated with Wi-Fi AP"
        break
    fi

    sleep 1
done

if ! iw dev wlan0 link | grep -q "Connected"; then
    echo "[-] Failed to associate with Wi-Fi AP"
    iw dev wlan0 link
    exit 1
fi

echo "[+] Starting DHCP client"

dhclient wlan0

echo "[+] Network configuration:"
ip addr show wlan0
ip route

if [ -n "$DECOY_PORT" ]; then
    echo "[+] Starting decoy banner listener on :$DECOY_PORT"
    printf '%b' "$DECOY_BANNER" >/etc/decoy-banner
    socat -T2 "TCP-LISTEN:${DECOY_PORT},fork,reuseaddr" \
        EXEC:"cat /etc/decoy-banner" &
fi

echo "[+] Starting kiosk web service"

exec nginx -g "daemon off;"
