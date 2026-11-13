# Backtrace

**Category:** Network Forensics
**Difficulty:** Medium
**Author:** Voyager 1

## Description (what the competitor will see)

Ship systems aboard the ISV Kestrel logged an unauthorized Modbus/TCP
write that disabled the `airlock-plc` safety interlock — while Cargo
Bay 2 was occupied.

You've been handed a full packet capture of the shipnet segment for the
shift in question, and the network's asset inventory. The write came
from the engineering console. Find out who was logged into it, how they
got the credentials to do so, and where those credentials actually
leaked from.

## Files Provided

- `dist/kestrel_shipnet.pcap` - full packet capture of the shipnet segment
- `dist/SHIP_SYSTEMS.md` - network asset inventory
- `dist/INCIDENT_REPORT.md` - the incident report: timestamp and source
  host of the malicious write

## Flag

`flag{never_ftp_your_secrets_into_space}`

## Solution

- `eng-console` (10.10.0.2) is the ship's engineering console — both a
  Telnet-managed terminal and the Modbus/TCP master that talks to OT
  devices on the shipnet segment.

1. Player filters `modbus` (or `tcp.port == 502`) and finds the lone
   **Write Single Coil (FC05)** request writing coil 0 → 0 at
   2024-06-15 02:22:44 UTC from `eng-console` — this is the incident
   already described in `INCIDENT_REPORT.md`, and disables
   `airlock-plc`'s safety interlock coil.
2. Player filters `telnet`, follows the TCP stream into `eng-console`
   around that timestamp, and recovers `rvoss` / `Kestrel#Eng77` in the
   clear — sent from `mtx-47` (10.10.0.47), an unassigned shared
   maintenance terminal, not R. Voss's own workstation.
3. Player traces further back: filters `ftp` / `ftp-data`, and uses
   **File → Export Objects → FTP** (or Follow TCP Stream, raw) to pull
   `eng_accounts.bak.gz` off the wire — uploaded earlier in the capture
   from `voss-ws` (10.10.0.15, Voss's actual workstation) to
   `shipnet-fs` (10.10.0.5) over plaintext FTP.
4. Player `gunzip`s the exported file (Wireshark doesn't auto-decompress
   FTP payload — it must be saved and decompressed manually). The
   decompressed file contains the same leaked credentials and the flag.

The lesson: an unauthenticated OT protocol (Modbus/TCP) plus an
unsegmented network plus a plaintext credential backup adds up to a full
compromise chain, even though no single step looks alarming in
isolation.

## Solve Script

See `solution/solve.py`:

```bash
cd solution
pip install -r requirements.txt   # scapy
python solve.py ../dist/kestrel_shipnet.pcap
```

Expected: it prints the malicious Modbus write, the recovered Telnet
credentials, the matching leaked backup content, and the flag.

## Techniques / Tags

`wireshark`, `pcap`, `forensics`, `modbus`, `ftp`, `telnet`, `credential-leak`

## Setup / Deployment Notes

No live service — this is a static pcap handout. The dist pcap is
generated, not hand-crafted, so it can be rebuilt or tuned
deterministically (fixed RNG seed):

```bash
cd src
python -m venv venv        # if not already present
./venv/Scripts/pip install -r requirements.txt
./venv/Scripts/python gen_pcap.py -o ../dist/kestrel_shipnet.pcap
```

This prints the packet count and the flag for verification. All story
constants (hostnames, IPs, credentials, backup content, timing) live at
the top of `src/gen_pcap.py` — change `FLAG`, `BACKUP_CONTENT`, and the
host dictionaries to reuse this shape for a different event.
`random.seed(1337)` keeps packet timing/ports reproducible across
regenerations as long as the sequence of calls in `build_capture()`
doesn't change.

## Known Issues / Notes

The backup is gzip'd before transfer because that's what a real backup
tool would actually produce — and, usefully, it also means a flat
`strings kestrel_shipnet.pcap | grep flag` does not find the flag, since
the bytes on the wire are compressed binary, not plaintext. Recovering
it requires actually pulling the file out of the FTP data stream and
decompressing it: a genuine, realistic Wireshark technique, not a
planted obstacle.
