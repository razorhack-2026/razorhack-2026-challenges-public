# Door Stuck — Writeup

Add a normally-open `DOOR_3` contact in series with an OTU coil named
`DOOR_3_COMMAND`. Submit the program. The door-close simulation appears in the
camera view and the flag is returned.

Flag: `flag{ord3r_r3st0r3d}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
