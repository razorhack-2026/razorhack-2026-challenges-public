# Uplink Login — Writeup

Inspect the page's cookies and character grid. Sort the cookie coordinates by
their step numbers and use them to read the access code from the grid. Submit
the code with a crew ID in the required format to authenticate.

Flag: `flag{ST4RS}`

## Local testing

From `src/`, run `docker compose up --build`. The challenge is available at
`http://localhost:8080` by default; set `CARGO_BAY_HTTP_PORT` to choose another
host port.
