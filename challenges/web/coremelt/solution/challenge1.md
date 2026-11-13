# Coremelt: Foothold — reference solution (GM only)

**Scores:** the web-foothold flag at `/flag.txt`. **Part 1 of 4.**

## Deploy

The whole Coremelt chain runs as one two-container stack that lives in **this
folder** (`docker-compose.yml`, `build.sh`, `src/`). Deploy once and all four
challenges point at it:

```
./build.sh        # builds the matiec base image, then the stack
```

Player-facing service: `http://<host>:3000` (only `corewatch-web` is published;
`eng-ws` shares its network namespace and listens on 127.0.0.1 only).

## Solve

Port 3000 serves the **CoreWatch reactor dashboard** (flavour — live gauges, a
locked coolant-interlock control panel, an ICARUS event stream). Its nav points
at **Engineering / RTU Control / Admin** consoles, and every GET to those
(`/admin`, `/engineering`, `/rtu`, `/controls`, ...) returns **HTTP 404**, as if
a middleware auth layer is hiding them. This *looks* like a Next.js middleware
auth gate (CVE-2025-29927, `x-middleware-subrequest`) but is a **decoy**: there
is no console behind it, and the dashboard's own controls are inert. Chasing the
middleware bypass / hidden admin route is the intended time-sink. The real bug is
on the server-action POST path to `/`.

`next@15.0.3` / `react@19.0.0` ship the vulnerable RSC "Flight" deserializer
(**CVE-2025-55182 / "React2Shell"**). A crafted multipart server-action request
walks the prototype chain to the global `Function` constructor and runs attacker
JS in the server process:

- headers `Next-Action: <any>`, `Accept: text/x-component`
- field `0` = a Flight model, `value` `{"then": "$B0"}`, `_response._formData.get`
  = `$1:constructor:constructor`, `_response._prefix` = the JS body
- field `1` = the literal `"$@0"`

Gotchas: no lexical `require` in that scope — use `process.mainModule.require`;
output is exfiltrated error-based (no egress) via a `NEXT_REDIRECT` `digest`.
See `solution/exploit_react2shell.py`.

`cat /flag.txt` → this challenge's flag.

## Verify with the reference solver

```
cd solution && python3 solve.py <host> 3000
```

The shared solver drives the entire chain and prints `ACCEPTANCE: PASS — 4/4
flags`. This challenge's flag is the one logged at stage `[1]`. Full-chain
detail is in `solution/challenge4.md`.

## Not trivially solvable another way

The middleware decoy has no route behind it; the CVE-2025-29927 path is a dead
end by design. The flag requires actual RCE, not the bypass.
