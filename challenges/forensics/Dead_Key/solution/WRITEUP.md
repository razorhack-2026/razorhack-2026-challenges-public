# Dead Key — Solution

`console_capture.pcap` is a ~2,400-packet capture of the relay station's local
network from about half an hour before contact was lost. Most of it is noise.
The useful traffic is MQTT telemetry from five crew biomonitors to the
station's broker (`10.13.40.50:1883`), and the point of the challenge is
cutting through the noise with filters.

## What's in the capture

Statistics > Protocol Hierarchy, or Statistics > Conversations, shows the
shape quickly:

- Five MQTT sessions, one per crew biomonitor (`10.13.40.21` to `.25`), all to
  the broker. This is the bulk of the packets.
- Background chatter: ARP, DNS, NTP and ICMP. Pure noise.
- Three short plaintext chat sessions (`tcp.port == 6667`). Flavor; none of it
  is part of the answer.

## Finding the time of death

Filter to `mqtt`. Each `PUBLISH` shows a topic and a value, and topics are
per-crew: `relay07/crew/<badge>/vitals/heart_rate`, `.../vitals/o2`, and
`.../link/heartbeat`. Two traps and one shortcut:

- `.../link/heartbeat` is a connection-liveness counter, not a pulse. Searching
  for "heart" by topic name and grabbing this one gives a meaningless number.
- Scrolling for the last packet doesn't work: four of the five monitors keep
  reporting for about three minutes after the death. The end of the capture
  isn't the answer.
- There is also a harmless `relay07/alerts/warning` from a different crew member
  (an elevated stress index). It is not the answer.

Any of these filters finds the right monitor:

- `mqtt.topic contains "critical"` goes straight to the one critical alert.
- `mqtt.topic contains "heart_rate" && mqtt.msg == "0"` returns a single
  packet: only `cm-0417` ever reads **0**.
- `tcp.flags.reset == 1` shows exactly one reset, from `10.13.40.23`, the same
  host. Every other session just keeps going, and this one is cut off with no
  graceful MQTT disconnect.

`cm-0417`'s heart rate declines across the session and flatlines to 0, then the
critical alert follows. The alert text deliberately carries **no** timestamp
(`strings | grep 2091` finds nothing); the time of death is the alert packet's
own capture time:

```
CREW CM-0417 :: LIFE SUPPORT FAILURE :: NO BIOMETRIC RESPONSE
```

Three independent signals (flatline reading, critical alert, abrupt connection
loss) land in the same second. In Wireshark use View > Time Display Format > UTC
Date and Time of Day, read the alert frame's time, drop the fractional seconds,
and format it as `YYYY-MM-DD_HH-MM-SS`:

`flag{...}`

(The packets are dated 2091, so a default local-time display needs switching to
UTC. The NTP packets in the background carry capture-consistent times too.)

## Solver

`solve.py` finds the critical alert, checks that the flatline reading and the
reset from the same host fall in the same second, and builds the flag from the
alert's UTC capture time.
