# Coremelt: Deeper In — reference solution (GM only)

**Scores:** `~/flag.txt` on the OT workstation, read after the SSH pivot.
**Part 3 of 4.** Requires the cracked engineer password from Part 2.

## Deploy

Shared stack — deploy from `challenges/web/coremelt/` (`./build.sh`).

## Solve

`/app/.env` on the web container (readable via the RCE) breadcrumbs the second
host: `PLC_WS_HOST=127.0.0.1`, `PLC_WS_USER=j.reyes`. `eng-ws` is a second
container sharing the web container's network namespace, with its SSH and PLC
bound to **127.0.0.1 only** — reachable only from inside the web foothold. SSH
there is never player-facing.

Pivot from the foothold and log in as `j.reyes` with the reused password
(`supernova1`), then read the flag in the home directory:

```
ssh j.reyes@127.0.0.1     # from inside the corewatch-web container
cat ~/flag.txt
```

The reference solver does this non-interactively with `SSH_ASKPASS_REQUIRE=force`
(OpenSSH ≥ 8.4), since the foothold shell has no TTY.

## Verify with the reference solver

```
cd solution && python3 solve.py <host> 3000
```

This challenge's flag is the one logged at stage `[3]` ("~/flag.txt on OT
host"). It lives only on `eng-ws` (a separate container), so it requires the
actual SSH login — the web RCE cannot read it directly.
