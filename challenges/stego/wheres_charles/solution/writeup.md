# Where's Charles? — Writeup

The shift brief identifies Harvey's last duty record as shift log 243. Use that
clue to request the hidden authenticated route:

`/audio/SHIFT_LOG_243.mp3`

Read the `Title`, `Subtitle`, and `Album artist` metadata fields in order and
concatenate their values. The result is a hexadecimal string; convert it from
hex to text, then Base64-decode that text to recover the flag.

Flag: `flag{fl04tInG_thRu_Sp4C3}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
