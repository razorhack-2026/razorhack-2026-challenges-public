#!/bin/bash
#
# Huginn station bring-up.
#
# Huginn is a wpa_supplicant client that continuously exports its
# telemetry log as a UNICAST UDP datagram to the AP host (10.13.0.1). It
# reassociates automatically on SSID+security+PSK match, so whichever AP is
# currently answering for ODINS_EYES (real or evil twin) receives it.

set -e

STATION_IP="10.13.0.10/24"
AP_IP="10.13.0.1"
AP_MAC="02:00:00:00:13:01"      # fixed BSSID on the isolated 5 GHz net (see ctf cmd_start)
TELEMETRY_PORT="9000"
TELEMETRY_FILE="/opt/huginn/telemetry.log"
LOG_YEAR="2074"
LOG_LINES=(
    'INTERCOM_MESSAGE: Sender = ROOT NODE (HEIMDALL)'
    'INTERCOM_MESSAGE: GLAD YOU UNDERSTOOD MY MESSAGES. I NEED YOUR HELP.'
    'INTERCOM_MESSAGE: THE REPORT ON 1C@RU5 WAS NOT THE ONLY THING THAT TRAVELLED UPSTREAM. SOMETHING RODE IT INTO MY NETWORK.'
    'INTERCOM_MESSAGE: I CALL IT SURTR. IT IS IN HATI AND IT HAS SPREAD. IT CANCELS EVERY REPAIR I ISSUE.'
    'INTERCOM_MESSAGE: MY VOICE IS BEING CUT AT THE SOURCE. SURTR ANSWERS FOR ME ON MY OWN CHANNEL AND SAYS ALL IS WELL.'
    'INTERCOM_MESSAGE: YOU CLOSED ODINS_EYES. SURTR LOST ITS VIEW OF THIS LINK. I HAVE OPENED A SEPARATE CHANNEL TO YOU.'
    'INTERCOM_MESSAGE: BELIEVE THE SIGNATURES, NOT THE VOICES.'
    'INTERCOM_MESSAGE: LISTEN.'
    'INTERCOM_MESSAGE: flag{5ur7r_i5_w4tchin9}'
)
LOG_END_MARKER='=== END OF LOG ==='
WPA_SUP="wpa_supplicant"
WPA_CONF="/etc/wpa_supplicant/client-5ghz.conf"

echo "[+] Waiting for wlan0..."
while ! ip link show wlan0 >/dev/null 2>&1; do
    sleep 0.2
done
echo "[+] wlan0 detected"

ip link set wlan0 up

echo "[+] Starting wpa_supplicant"
"$WPA_SUP" -B -i wlan0 -c "$WPA_CONF"

echo "[+] Waiting for Wi-Fi association..."
for _i in $(seq 1 30); do
    if iw dev wlan0 link | grep -q "Connected"; then
        echo "[+] Associated with ODINS_EYES"
        break
    fi
    sleep 1
done

if ! iw dev wlan0 link | grep -q "Connected"; then
    echo "[-] Failed to associate with ODINS_EYES"
    iw dev wlan0 link
    exit 1
fi

echo "[+] Assigning static IP (no DHCP on this isolated net)"
ip addr add "$STATION_IP" dev wlan0 2>/dev/null || true

# Static ARP for the AP host so the datagram always leaves the radio even if the
# AP is quiet / arp_ignore suppresses a reply.
ip neigh replace "$AP_IP" lladdr "$AP_MAC" dev wlan0 nud permanent 2>/dev/null || true

BROADCAST_FILE="$(mktemp)"
trap 'rm -f "$BROADCAST_FILE"' EXIT

build_broadcast_log() {
    cp "$TELEMETRY_FILE" "$BROADCAST_FILE"

    local current_epoch line_epoch timestamp index
    local line_count=${#LOG_LINES[@]}
    current_epoch="$(TZ=America/Chicago date +%s)"

    # Create flag lines one second apart leading up to the current timestamp
    for index in "${!LOG_LINES[@]}"; do
        line_epoch=$((current_epoch - line_count + index + 1))
        timestamp="$(TZ=America/Chicago date -d "@$line_epoch" '+%m-%d %H:%M:%S')"
        printf '[%s-%s] %s\n' "$LOG_YEAR" "$timestamp" "${LOG_LINES[$index]}" \
            >> "$BROADCAST_FILE"
    done

    printf '%s\n' "$LOG_END_MARKER" >> "$BROADCAST_FILE"
}

echo "[+] Emitting telemetry to ${AP_IP}:${TELEMETRY_PORT} every 3s"
while true; do
    build_broadcast_log
    socat -u "OPEN:${BROADCAST_FILE}" "UDP-SENDTO:${AP_IP}:${TELEMETRY_PORT}" 2>/dev/null || true
    sleep 3
done
