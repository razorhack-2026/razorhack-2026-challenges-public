# GM verification: Minor Calculations

Run commands from challenges/misc/life/ using Python 3.12.

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

HTTP service. `GET /api/status` returns a random instance `id` plus constraints.
Players solve for `N2` and `O2` and `POST /api/mix` with that id.

The numbers change every request and the id dies in **5 seconds**, so this has to
be a script. Tolerance is 0.05.

The service flag in `challenges/misc/life/src/app.py` (or `LIFE_FLAG`) must match
`challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
