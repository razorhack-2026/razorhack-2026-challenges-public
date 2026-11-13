# Another Flashing Light — Writeup

Add three rungs to the program:

- `SENSOR_0` normally-open contact to `CONTAINER_ALARM_0_WRITE`
- `SENSOR_1` normally-open contact to `CONTAINER_ALARM_1_WRITE`
- `SENSOR_2` normally-open contact to `CONTAINER_ALARM_2_WRITE`

Use an OTE coil for each output. Submit the program to receive the flag.

Flag: `flag{cont41n3r_is_g0n3?}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
