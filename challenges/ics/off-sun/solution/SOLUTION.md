# Off-Sun — GM Solution

**Category:** ICS · **Difficulty:** Hard · **Author:** Jebediah Kerman

**Flag:** `flag{d0nt_l00k_d1r3ctly_4t_th3_sun}`

> GM-only. Do not copy any of this into the competitor `README.md` or into `dist/`.

---

## Premise

The station's solar arrays drifted off-sun and output collapsed. The handout,
`dist/array_ctrl.pcap`, is a packet capture from the array control network segment.
A rogue device on that segment issued Modbus commands that walked the elevation
setpoint away from the sun, and it hid a message one byte at a time inside those
commands. Recovering the message gives the flag.

## Network / register map

Modbus server (the array controller) is **10.20.7.40**, listening on **TCP 1502**
(deliberately not the well-known 502).

| Host | IP | MAC | Role |
|---|---|---|---|
| Operator HMI | 10.20.7.10 | 00:1b:1b:11:22:33 | polls pointing registers |
| Historian | 10.20.7.20 | 00:1b:1b:77:88:99 | polls a wider block |
| Engineering WS | 10.20.7.11 | 00:1b:1b:44:55:66 | **legitimate** setpoint writes |
| **Rogue device** | 10.20.7.11 | **52:54:00:de:ad:be** | spoofs the eng-WS IP; the malicious writes |

Holding registers on the controller:

| Reg | Dec | Meaning | Access in capture |
|---|---|---|---|
| 0x0064 | 100 | azimuth feedback (×10 deg) | read (FC03) |
| 0x0065 | 101 | elevation feedback (×10 deg) | read (FC03) |
| 0x0066 | 102 | array power output | read (FC03) |
| 0x0067 | 103 | panel temperature (×10) | read (FC03) |
| 0x006E | 110 | mode (0=track / 1=manual) | rare legit write |
| **0x006F** | **111** | **elevation setpoint** | legit **and** rogue writes (FC06) |

## Intended solve path

1. **Recognize the protocol despite the port.** Opening the pcap, Wireshark shows
   plain TCP on port 1502 with no dissector. The payloads have the tell-tale Modbus
   MBAP shape (`transaction id`, `protocol id = 0x0000`, `length`, `unit id`).
   Right-click a packet → **Decode As… → Modbus/TCP** (or set the port to 502 in the
   Modbus preference). Everything now dissects as Modbus.

2. **Separate reads from writes.** The overwhelming majority is Read Holding
   Registers (FC03) polling — the HMI reading az/el, the historian reading the wider
   block. These never change state; ignore them. Filter to writes:
   `modbus.func_code == 6` (Write Single Register). That leaves a small set.

3. **Find the anomaly: one IP, two MACs.** Two hosts issue FC06 writes, and both use
   source IP **10.20.7.11**. But the Ethernet source MAC differs — `00:1b:1b:44:55:66`
   for most of them and `52:54:00:de:ad:be` for the rest. A single IP presenting two
   MAC addresses is the classic signature of a spoofed-IP / rogue device on the
   segment. (Wireshark: add `eth.src` as a column, or
   `modbus.func_code == 6 && eth.src == 52:54:00:de:ad:be`.)

4. **Note that register and IP alone don't isolate it.** Both the legitimate
   engineering workstation and the rogue write the *same* register (111, the setpoint)
   from the *same* IP, and the rogue's byte values (0x20–0x7E) overlap the legitimate
   setpoint range. So neither "unusual register" nor "unusual IP" nor "unusual value
   range" cleanly separates the attack — **the MAC is the only clean discriminator.**
   This is the intended difficulty.

5. **Decode the rogue writes.** For each FC06 write from the rogue MAC, take the
   register value's low byte as an ASCII character, in capture order:

   ```
   0x66 0x6C 0x61 0x67 0x7B ... → f l a g { ...
   ```

   The 35 bytes spell the flag. Decoding the *legitimate* MAC's setpoint writes
   instead yields gibberish (`()*+*)()...`), which confirms the MAC split was correct.

**Flag:** `flag{d0nt_l00k_d1r3ctly_4t_th3_sun}`

## Reference solver

`solution/solution.py` (stdlib only, no scapy). Run against the shipped artifact:

```
python solution/solution.py
```

It parses the pcap, keeps FC06 requests addressed to the server, reports the
one-IP-two-MAC anomaly, groups the setpoint writes by source MAC, and prints the
group that decodes to `flag{…}`. Verified end-to-end against `dist/array_ctrl.pcap`.

### One footgun worth knowing (for reviewers)

Modbus FC06 request and response PDUs are **byte-identical**. If you decode both
directions you double every character (`ffllaagg{{…`) and the controller looks like a
writer too. The solver keeps only packets addressed **to** the server (10.20.7.40);
in Wireshark, filter on request direction (`tcp.dstport == 1502`) or add the response
half deliberately when reasoning about it.

## Rebuilding

```
python src/generate.py            # writes dist/array_ctrl.pcap, deterministic on --seed
python solution/solution.py       # confirms the flag round-trips
```

Default seed is 1106. The flag string lives in `src/generate.py` (`FLAG`) and in
`challenge.yml`; keep them in sync if it ever changes. The flag never appears as
plaintext in `dist/` — each byte is only the low byte of a Modbus register value.

## Difficulty rationale

Four independent layers, all genuine analysis rather than bait (no decoy flags):
non-standard port (protocol recognition + Decode As), IP spoofing surfaced only by the
MAC mismatch, payload hidden on an actively-used register so IP/register/value don't
isolate it, and ~18.5k packets of realistic poll traffic burying ~35 malicious writes.
