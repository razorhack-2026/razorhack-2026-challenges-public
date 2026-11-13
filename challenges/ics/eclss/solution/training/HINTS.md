# Training Bay - Tiered Hints (staff)

**Nudge** (free / early) -> **Bigger** (mid-session) -> **Near-spoiler**
(behind a point cost). No flags here; those are in `SOLUTIONS.md`.

| # | Nudge | Bigger | Near-spoiler |
|---|-------|--------|--------------|
| MB1 | Function code 3 reads holding registers. Start at address 0. | It's one register; the number *is* the answer. | Read HR0, wrap the decimal value in `flag{}`. |
| MB2 | Ask for 16 registers in one read. | The values are all in the printable ASCII range. Split each into 2 bytes. | Low byte first: `bytes([v & 0xFF, v >> 8])`, then decode. |
| MB3 | `4xxxx` addresses are a numbering convention, not a register number. | The leading 4 means "holding register" and the rest is 1-based. | 40201 -> holding register 201 (1-based) -> 200 (0-based). |
| MB4 | Coils are bits you can write with function code 5. | Write coil 0 ON, then read HR300 before 15 s passes. | `write_coil(0, True)` then decode HR300-315. |
| MB5 | One register holds 16 bits; this value needs more. | High word first means HR400 is the top 16 bits. | `(HR400 << 16) \| HR401`. |
| MB6 | Those two registers aren't two numbers - they're one float. | Pack the two words as 4 big-endian bytes and unpack as `>f`. | `struct.unpack('>f', struct.pack('>HH', hi, lo))`, round to 3 places. |
| MB7 | Read the panel before you write it. | Set one bit with OR, keep the rest. A tripped panel stays tripped until reset. | Read HR1025, write `value \| (1 << 9)`. Trip? coil 30 ON, then retry. |
| PL1 | Read `FB_Airlock` - list every condition `Door_Open` needs. | One of those conditions is already "wrong" when the rig starts. | Override (coil 10) OFF, coils 8, 9, 11 ON, wait > 4 s. |
| PL2 | What does a TON do when its input goes FALSE? | Your input has to stay TRUE the whole preset time. | Coil 16 ON and leave it ON for 5+ s. |
| PL3 | The counter counts *edges*, not levels. | The PLC only looks every 100 ms. Two writes in the same 100 ms are one state. | 7x (ON, wait 300 ms, OFF, wait 300 ms), then leave it OFF 2 s. Too many? coil 18 resets. |
| PL4 | Read the comment on how STOP is wired. | Normally-closed: TRUE means *not pressed*. A motor can't start while STOP reads pressed. | Coil 25 ON, pulse coil 24 ON then OFF, wait 3 s. |
| PL5 | 4 mA isn't zero. | Scale over the 4-20 mA span: raw 6554 -> 0 %, raw 32767 -> 100 %. | raw = 6554 + 0.625 x (32767 - 6554) = 22937. |
| IG1 | Gateways answer some pages without a login. | Monitoring tools check gateway liveness with a status route. | Try the gateway's `StatusPing` / gwinfo routes and its landing page. |
| IG2 | "Hidden" can just mean "styled to be invisible." | Open your browser's developer tools and look at the page's elements, not the screen. | Inspect the DOM near the bottom-right corner of the screen. |
| IG3 | The clue is a famous radio-astronomy frequency. | 21 cm wavelength; give the frequency in MHz, no decimals. | 1420. Type it and press Enter. |
