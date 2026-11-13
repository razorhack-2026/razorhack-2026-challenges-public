# GM verification: CORE: Queen Bot Protocol

Run commands from challenges/misc/core/ using Python 3.12.

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

CORE intentionally requires the seven earlier clearance tokens. The reference verifier reads the seven GM prerequisite tokens from prerequisites.txt so this PR can be tested alone. That GM-only fixture is not a competitor download; CORE still requires players to earn the earlier tokens.

## Reference approach (GM only)

HTTP service. `POST /api/override/auth` with all seven earlier flags returns a
session and a 4x4 Lights Out grid. `POST /api/override/grid` applies presses
(cell plus orthogonal neighbors). All zeros returns the flag. Move budget is 20.

`REQUIRED_TOKENS` in `challenges/misc/core/src/app.py` must list the other seven flags
exactly. Miss one and the boss is unsolvable. The `FLAG` hardcoded in `src/app.py`
must match `challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order.

At the event each team starts its own copy from CTFd: topic `instance:core`, entry `core` in Razorhack-Infra's `lib/challenges.json`, port 8082. CTFd fills `{host}` and `{port}` into `connection_info`. The flags are baked into the image, so there is no flag secret to put. Keep gunicorn at its default single worker: game sessions live in that worker's memory.
