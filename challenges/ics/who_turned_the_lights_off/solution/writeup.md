# Who Turned The Lights Off — Writeup

Add one rung for each light output. Each rung has a normally-closed
`SHUTDOWN_0` contact driving an OTE coil:

- `LIGHT_0_WRITE`
- `LIGHT_1_WRITE`
- `LIGHT_2_WRITE`

Submit the program to receive the flag.

Flag: `flag{l4t_th3r3_b3_l1ghts}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
