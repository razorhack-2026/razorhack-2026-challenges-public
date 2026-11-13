# Chain of Command — crew-services authorization tags

`authtag.py` is the crew-services back office's own module for signing authorization
records. It is published here for reference. It is exactly the code the service uses,
with one thing removed: the signing key.

## The scheme

Every authorization record is signed with a keyed tag over its canonical form:

```
M = "{request_id}|{subject_id}|{resource_id}|{status}|{nonce}"
x = int.from_bytes(sha256(M.encode()), "big") % p          # p = 2**31 - 1
T = (a*x*x + b*x + c) % p                                   # the authorization tag
```

- `p` is public (the Mersenne prime `2147483647`).
- `a`, `b`, `c` are the back office's secret signing key — the **same** triple for every
  record — read from the environment (`AUTH_A` / `AUTH_B` / `AUTH_C`). They are **not**
  included in this copy, so `authtag.coefficients_from_env()` returns `None` here.

`authtag.py` gives you `canonical_message`, `message_point` (the `x` map), `compute_tag`
(given a key), and `recover_coefficients` (a helper that solves for a key from signed
records over `GF(p)`).

## The service

The crew-services console speaks JSON (see the footer on the page). A session's own crew
ID comes from `GET /api/whoami`; `GET /api/approvals` lists historical authorization
records; `POST`/`GET`/`PATCH /api/requests` manage your own requests; and PURSER opens the
command archive once it can verify an approved authorization for you.

Flag format: `flag{...}`.
