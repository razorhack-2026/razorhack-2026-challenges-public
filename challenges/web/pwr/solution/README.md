# GM verification: Reactor Access

Run commands from challenges/web/pwr/ using Python 3.12.

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

HTTP service with a login page. Any crew ID logs in at player clearance. SCRAM
needs `role: admin`.

The login page loads `/static/config.js`, which leaks the HS256 signing secret.
Forge a JWT with `role: admin` and send it as the `pwrToken` cookie (or
`Authorization: Bearer`) on `POST /api/reactor/scram`. The UI never shows the
token; it only lives in the cookie.

The secret must be at least 32 bytes (RFC 7518 / current PyJWT). Default:

```
microbot_leak_2024_replace_before_prod
```

The service flag in `challenges/web/pwr/src/app.py` (or `PWR_FLAG`) must match
`challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
