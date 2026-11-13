# Name Resolution

**Category:** Forensics (Network) · **Difficulty:** Medium

Something is off with console KOT-CONSOLE-7 in Docking Ring 3. It passes every
health check, but the comms team keeps catching it talking past the convoy —
reaching for a contact that isn't on any of our boards.

We pulled a short capture of its traffic during one of these spells. Most of it
is the usual internal chatter. Intel is certain the console is *saying* something
to whoever is out there, but there is no obvious upload, no file transfer,
nothing on the ports you'd watch. Find what left, where it was going, and what
it was carrying.

## Provided

- `capture.pcap` — a short span of the console's network traffic.

## Flag

Standard `flag{...}` format.
