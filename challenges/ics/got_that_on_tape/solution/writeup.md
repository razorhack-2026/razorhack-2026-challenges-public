# Got That On Tape — Writeup

In the PLC editor, add a normally-closed `SHUTDOWN_0` contact in series with an
OTE coil named `CAMERA_0_WRITE`. Compile and submit the program. The simulated
camera comes online and the site returns the challenge flag.

Flag: `flag{1_c4n_s33_cl34rly_n0w}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
