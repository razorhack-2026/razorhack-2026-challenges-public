# ISV Kestrel — Shipnet Anomaly Report

**Filed by:** Ship Systems Security
**Severity:** High

---

At **2024-06-15 02:22:44 UTC**, ship systems logged an unauthorized
Modbus/TCP write disabling the `airlock-plc` safety interlock coil
(coil 0) aboard the ISV Kestrel. Cargo Bay 2 was occupied at the time
per the crew manifest.

**Source host:** `10.10.0.2` (`eng-console`)

## Your objective

**You're looking for a recovery token in `flag{...}` format, hidden inside a
file that leaked onto the shipnet during this shift.** Find out who was
logged into `eng-console` when the write went out and how they got in —
then work backward from there to where it actually started.

## Provided files

- `kestrel_shipnet.pcap` — full packet capture of the shipnet segment
  spanning the shift in question
- `SHIP_SYSTEMS.md` — network asset inventory
