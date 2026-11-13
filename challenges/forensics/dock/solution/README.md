# GM verification: DOCK: Airlock Handshake

Run commands from challenges/forensics/dock/ using Python 3.12.

~~~sh
python -m pip install -r solution/requirements.txt
~~~

Start the local service first:

~~~sh
docker compose up -d --build
~~~

After verification, stop it with docker compose down.

~~~sh
python solution/verify.py
~~~

The verifier captures solver output, compares the recovered flag exactly with challenge.yml, and reports only PASS/FAIL. Do not paste direct solver output into logs, PRs, or public documentation. Static solvers use only dist/; service solvers use the local exposed interface.

## Reference approach (GM only)

File plus a live TCP service. The pcap shows a successful OPEN, a replay of the
same nonce (rejected), and an HTTP decoy that leaks `hmac_key=dock_reliant`.

Frame layout: `MICROBOT` + cmd (1) + nonce (4 LE) + SHA256(key + cmd + nonce)[:8].
`CMD_OPEN` is `0x01`. The nonce `0x00001234` from the capture is already spent on
the service. A fresh OPEN returns the flag.

The service flag in `challenges/forensics/dock/src/app.py` (or `DOCK_FLAG`) must match
`challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
