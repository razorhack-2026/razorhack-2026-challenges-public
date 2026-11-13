# GM notes: Cryopod Wake Sequence

The intended solve is a timing attack against the left-to-right wake-code comparison. Each correct leading digit adds the configured delay. The client tries candidate digits, measures response times, and waits for the advertised rolling attempt window before continuing. A request beyond the limit vents the pod and changes its code.

The server uses only the Python standard library. Set `FLAG` in the service environment, then run `docker compose up --build` from this folder to start it on port 8000. The default timing is designed for a live event; `DIGIT_DELAY`, `JITTER`, `TRIES`, and `WINDOW` are environment settings for controlled testing and deployment.

Run `python solution/test_server.py` from this folder to verify the reference solve, the rate-limit reset, timing signal, and invalid-request handling. The test uses shortened delays, compares the recovered value with `challenge.yml`, and emits no flag values.
