# Under Pressure — Writeup

Create a rung with three normally-closed contacts for `DOOR_1`, `DOOR_2`, and
`DOOR_3` in parallel, driving the OTE coil `PRESSURE_ALARM_0_WRITE`. Submit the
program in the PLC editor. The rung matches the pressure alarm logic and
returns the flag.

Flag: `flag{crU5h1ng_d0wN_oN_m3}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
