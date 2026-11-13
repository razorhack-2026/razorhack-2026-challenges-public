# Cargo Bay Forensics — Writeup

Download `cargo_bay_traffic.pcap` from the uplink and inspect the Modbus/TCP
and UDP conversations. The Modbus writes from `172.30.0.50` originate from a
host not listed in the Cargo Bay 12 manual. The writes set
`shutdown_0_command` and `door_3_command` to true. Inspecting the UDP payload
from that host reveals a payload in Base64, decoding this payload results in the flag.

Flag: `flag{g0T_y0uR_CArG0!}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
