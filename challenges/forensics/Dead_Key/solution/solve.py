"""Reference solution for Dead Key.

Finds the one MQTT PUBLISH to the telemetry broker's critical-alerts topic.
The alert text has no timestamp; the time of death is the packet's own capture
time, in UTC, rounded down to the second. Also checks that the flatline reading
and the connection reset from the same host fall in the same second.

Run: python solve.py [path/to/console_capture.pcap]
     (defaults to ../dist/console_capture.pcap)
"""
import os
import sys
from datetime import datetime, timezone

from scapy.all import rdpcap, TCP, IP
from scapy.contrib.mqtt import MQTT, MQTTPublish

ALERT_TOPIC = b"relay07/alerts/critical"


def main():
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "console_capture.pcap")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    pkts = rdpcap(path)

    def stamp(pkt):
        return datetime.fromtimestamp(float(pkt.time), timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    alert = None
    flatline = None
    reset = None
    for pkt in pkts:
        if pkt.haslayer(MQTT):
            pub = pkt.getlayer(MQTTPublish)
            if pub is None:
                continue
            if pub.topic == ALERT_TOPIC:
                alert = pkt
            elif pub.topic.endswith(b"/vitals/heart_rate") and pub.value == b"0":
                flatline = pkt
        elif pkt.haslayer(TCP) and pkt[TCP].flags & 0x04:        # RST
            reset = pkt

    if alert is None:
        raise SystemExit("no critical alert publish found -- capture may be wrong")

    tod = stamp(alert)
    for name, pkt in (("flatline", flatline), ("reset", reset)):
        if pkt is None or stamp(pkt) != tod or pkt[IP].src != alert[IP].src:
            raise SystemExit(f"{name} packet does not agree with the alert -- capture may be wrong")

    flag = f"flag{{{tod}}}"
    print(f"[+] time of death (UTC): {tod}")
    print(f"[+] FLAG: {flag}")


if __name__ == "__main__":
    main()
