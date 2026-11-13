# Ghost Command

**Category:** ICS
**Difficulty:** Medium
**Author:** Voyager 1

## Description (what the competitor will see)

See `README.md` — analyze a maintenance-window pcap of IEC 61850 GOOSE
traffic between two IEDs, find the one genuine trip frame hiding among
decoys, and replay it onto the live segment to trip the breaker for real.

## Files Provided

- `dist/substation_test_window.pcap` — full capture of the maintenance
  test window (~2 minutes), containing every GOOSE frame both IEDs sent.

## Flag

`flag{one_frame_wasnt_a_drill}`

## Solution

1. Open `substation_test_window.pcap` in Wireshark. Filter on `goose` —
   every frame in the capture dissects natively (EtherType `0x88b8`, no
   IP/TCP underneath).
2. There are two distinct GOOSE control blocks in play:
   - `IED_PROT03LLN0$GO$gcbTrip` — the protection relay's trip command.
   - `IED_BKR07LLN0$GO$gcbPos` — the breaker's own position echo, published
     locally whenever a technician racks it open/closed. This is a decoy:
     it toggles a boolean just like a trip does, but it isn't a command
     IED-BKR-07 reacts to at all.
3. Filter to the trip control block only:
   `goose.gocbRef == "IED_PROT03LLN0$GO$gcbTrip"`. Most frames carry
   `boolean = False` (steady "no trip" heartbeat). A handful carry
   `boolean = True` — a rehearsed exercise the crew ran through on purpose.
4. The tell isn't the trip value, it's Wireshark's `goose.simulation` field
   (labeled "Simulated" in the dissected tree; this is the IEC 61850-8-1
   field historically called `test` — Edition 2 renamed it). A compliant
   GOOSE subscriber must never act on a frame with this flag set unless it
   is itself in test mode. Every rehearsed trip in the capture has
   `simulation = True`. Exactly one frame — `stNum=6, sqNum=0` — has
   `simulation = False` *and* `boolean = True`. That's the real one:
   `goose.simulation==0 && goose.boolean==1` narrows 89 GOOSE frames down
   to exactly 1.
5. Export that frame's raw bytes (Wireshark: right-click → Copy → ...as a
   Hex Stream, or `tshark -r ... -Y "frame.number==94" -x`) and replay it
   onto the wire from the jump box. GOOSE has no session state, sequence
   validation, or authentication — the subscriber has no way to tell a
   replayed frame from the original.
6. IED-BKR-07 accepts the frame, trips (Modbus holding register 1 flips to
   `1`), and unlocks the flag in holding registers 100+.

## Solve Scripts

Split into two self-contained scripts because the dist pcap lives on the
GM/competitor's own machine, not on the jump box — there's no way to copy
the pcap file itself onto the jump box without going through docker, so
parsing has to happen locally and only the result crosses over:

1. `solution/find_frame.py` — run **locally** against the downloaded pcap,
   no network needed. Has its own copy of `src/common/goose.py`'s BER
   decoder inlined (never shipped to competitors, who do the equivalent by
   hand in Wireshark). Filters to `IED_PROT03LLN0$GO$gcbTrip` frames with
   `boolean == True`, picks the one with `test/simulation == False`
   (asserts there's exactly one — if the capture ever regenerates with a
   different shape, this is the canary that catches it), and prints that
   frame's raw bytes as a hex string:
   ```
   python3 find_frame.py substation_test_window.pcap
   ```
2. `solution/replay.py` — run **on the jump box**, a single file with no
   other solution/ dependency. Takes the hex string from step 1, opens a
   raw `AF_PACKET` socket on `eth0` and replays those exact bytes (needs
   `sudo` — raw sockets need root even with the container's `NET_RAW`
   capability, since `player` isn't the container's default user), then
   reads IED-BKR-07's Modbus holding registers to confirm the trip landed
   and pull out the flag:
   ```
   sudo python3 replay.py <hex-string-from-step-1>
   ```

## Techniques / Tags

- IEC 61850-8-1 GOOSE protocol analysis (Wireshark's native GOOSE
  dissector).
- Distinguishing dataset/message semantics from raw message shape — two
  different control blocks look similar at a glance; the deciding field
  isn't even the one that seems most obviously "the trip."
- Raw L2 frame injection / replay attack against a protocol with no
  session state or replay protection (`NET_RAW`, `scapy`/raw sockets).

## Setup / Deployment Notes

- `docker-compose.yml` brings up three containers on `substation_net`
  (`10.13.39.0/24`): `ied-prot` (publisher, no exposed ports), `ied-bkr`
  (subscriber + Modbus/TCP status on `:502`), and `jump` (SSH on host
  `2223`, forwarded to container `22`).
- **GOOSE frames use the Ethernet broadcast address (`ff:ff:ff:ff:ff:ff`),
  not a real IEC 61850 multicast MAC (`01:0C:CD:01:xx:xx`).** Real
  deployments use multicast; broadcast was chosen here to sidestep Docker
  bridge multicast-snooping edge cases (a Linux bridge's default
  `multicast_snooping=1` can restrict multicast flooding to ports that
  sent an IGMP join, which none of these containers do since GOOSE isn't
  IGMP-aware). Broadcast is always flooded, guaranteeing delivery
  regardless of the bridge's multicast configuration on whatever host this
  gets deployed to. Wireshark's GOOSE dissector doesn't key off the
  destination MAC, so this doesn't affect the puzzle.
- **The live deployment never sends the genuine frame itself.**
  `src/ied-prot/publisher.py` has a `MODE` env var: `MODE=capture` (used
  once, offline, to generate the pcap) runs the full scripted test window
  including the one real trip; `MODE=live` (the default, what
  `docker-compose.yml` actually runs) loops heartbeats and *only*
  `test=True` rehearsal decoys, forever. This matters — an earlier version
  had the live publisher run the identical schedule including the genuine
  frame, which meant the live breaker would trip **on its own**, roughly
  90 seconds after the containers started, before any competitor even
  connected. Splitting capture/live modes was a direct fix for that: the
  incident now only exists in the historical pcap, and the only way to see
  it happen *now* is to find and replay that exact frame yourself.
- To regenerate `dist/substation_test_window.pcap` (e.g. if the schedule
  in `publisher.py` changes): `docker compose -f
  docker-compose.capture.yml up --build -d`, wait for the `sniffer`
  service to exit (~2 minutes), then copy `src/capture/out/
  substation_test_window.pcap` into `dist/`. This runs on an isolated
  `capture_net` (`10.13.49.0/24`) under its own Compose project name
  (`ghost_command_capture`) so it can't collide with, or accidentally
  attach to, the live `substation_net` stack. **Never point this at the
  live deployment** — `MODE=capture` really sends the genuine frame.
- `ied-prot` and `ied-bkr` both need `cap_add: NET_RAW` to open raw
  `AF_PACKET` sockets. `jump` additionally gets `NET_ADMIN` (unused by the
  intended solve, kept for parity with Blind Spot's jump box in case a
  competitor wants to sniff live traffic with `tcpdump`/`tshark` instead
  of only working from the provided pcap).
- GOOSE APDU encoding/decoding is hand-rolled (`src/common/goose.py`) —
  scapy has no built-in GOOSE/IEC 61850 layer. Verified against a real
  `tshark` GOOSE dissector (not just round-tripped against itself) before
  relying on it; see "Known Issues / Notes" below.

## Known Issues / Notes

- **Verified the encoder against a real dissector, not just itself.**
  Hand-rolling BER-TLV risks a self-consistent bug where encode and decode
  agree with each other but neither matches the real IEC 61850-8-1 wire
  format — which would only surface once a competitor opened the pcap in
  actual Wireshark. Built a throwaway `tshark`-equipped container
  (`ghost_command-jump` already ships `tshark`) and ran it against the
  generated pcap: `goose.gocbRef`, `goose.simulation`, `goose.stNum`,
  `goose.sqNum`, and `goose.boolean` all dissect correctly, and
  `goose.simulation==0` isolates exactly the one intended frame out of 89
  GOOSE frames captured. The field name surprise (Wireshark shows
  `goose.simulation`, not `goose.test`) turned out to be accurate, real
  Edition 2 terminology, not a dissector quirk — the README/this writeup
  reference "simulation flag" for that reason.
- **Found and fixed a real trivial-solve/no-solve-possible bug during
  build:** the first version of `ied-prot` ran the *same* scripted
  schedule (heartbeats, rehearsals, and the one genuine frame) regardless
  of context. That's fine for offline pcap generation, but it meant the
  live challenge deployment would also send the genuine frame on its own
  timeline — the breaker would already be tripped and the flag already
  unlocked roughly 90 seconds after `docker compose up`, with nothing left
  for a competitor to do (or worse, a mismatch between "what's in the
  pcap" and "what state the live service happens to be in" if they
  connected at a different moment). Fixed by adding `MODE=capture` /
  `MODE=live`: only capture mode ever transmits the real frame; live mode
  loops forever without it, so the trip can only happen when a competitor
  actually finds and replays the captured frame themselves.
- **Docker Compose project-name collision during capture testing:**
  `docker-compose.capture.yml` originally had no explicit `name:`, so
  Compose defaulted its project name to the working directory (same as
  the live `docker-compose.yml`), and both files' matching service keys
  (`ied-prot`, `ied-bkr`) collided — bringing up the capture file
  recreated the *live* containers in place (onto the isolated capture
  network) instead of creating separate ones, silently breaking the live
  deployment mid-test. Fixed by pinning `name: ghost_command_capture` at
  the top of `docker-compose.capture.yml` so the two stacks never share a
  project namespace.
- Full re-verification after both fixes: brought up the live stack fresh,
  confirmed it stays idle (breaker closed, `tripped=0`) indefinitely on
  its own, then ran `solution/find_frame.py` locally against the dist pcap
  and `solution/replay.py` from inside the `jump` container
  exactly as a competitor would (against the `dist/` pcap only) and
  recovered the exact flag from `challenge.yml`. Leak check
  (`grep -RnoE 'flag\{[^}]*\}' dist/ README.md`) clean.
- `time_allowed`/`confRev` values and the 802.1Q VLAN priority tag real
  substations typically add are omitted for simplicity — didn't affect
  dissection or the puzzle, and would only have added build time.
