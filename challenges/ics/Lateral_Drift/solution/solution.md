# Lateral Drift - Solution

*(2/3 of the "Lateral Drift" sequence. Gated by **Know Your Mark** (1/3)'s recovered VPN
credential; feeds **Last Mile** (3/3) via the engineering workstation's diagnostics page.)*

## Status: built + verified end-to-end, 2026-10-22

## Setup

1. Recover the VPN credential from **Know Your Mark**: `rootkit` / `icarus_override`.
2. `ssh rootkit@<vpn-gateway-host> -p <port>` with that credential.

## Hop 1 -> 2: the second credential

On vpn-gateway, `/opt/backups/eng-sync.tar.gz` is a world-readable backup (an unencrypted ops
mistake, not a bash-history scrollback - a concrete artifact to extract and grep). Inside:

```
workstation_host=127.0.0.1
workstation_port=5000
workstation_user=svc_eng
workstation_pass=EngSync_2087
```

## Hop 2 -> 3: the pivot

`engineering-workstation` is not reachable from outside at all: it shares `vpn-gateway`'s
network namespace (one Fargate task per team; `network_mode: service:vpn-gateway` locally) and
listens on `127.0.0.1:5000` only, so only a process on the gateway can reach it. From inside the
vpn-gateway SSH session:

```bash
curl -d "username=svc_eng" -d "password=EngSync_2087" http://127.0.0.1:5000/login -L
```

Logs in and renders the dashboard: an "Engineering Notes" panel with this challenge's flag, a
"Diagnostics" panel naming `process-plc`'s live Modbus/TCP host:port, and a **Documents** panel
linking the centrifuge controller's commissioning sheet (`/docs/rc200-commissioning`). The sheet holds
Last Mile's register map and the controller's factory default unlock code, so it is Last Mile's
only handout. It is login-protected (HTTP 302 to the login page without a session).

This challenge's own flag is still on the dashboard, reachable without opening the Documents panel.
That is intentional: the checkpoint is "reached the workstation"; the documents are for Last Mile.
`src/engineering_workstation/config.py` keeps `PLC_UNLOCK_CODE`, which must equal Last Mile's
`DEFAULT_UNLOCK_CODE`.

## Solve Script

```bash
pip install -r solution/requirements.txt
python solution/solve.py --host <vpn-gateway-host> --port <ssh-port>   # 22 on the Fargate copy, 2223 locally
```

Does all three hops (SSH, extract+recover the second credential, pivot+login) and prints the
flag plus the Last Mile hand-off info.

## Flag

`flag{the_second_door_was_never_locked}` - **draft**, matches `challenge.yml`; confirm or
replace, same as the other two parts' flags.

## Techniques / Tags

`ssh-foothold`, `credential-hunting`, `network-pivot`, `internal-segmentation`, `weak-auth`

## Operability

- **Expected solve time:** 10-20 minutes (SSH in, notice/extract the world-readable backup
  tarball, recognize the second credential, realize the workstation isn't reachable except by
  pivoting from inside the vpn-gateway shell, log in). A blind stranger-test agent (README +
  connection info only, no solution/src) solved it in ~9 tool calls with zero conceptual stalls -
  fully linear once attempted, which is why this is tagged Medium rather than Hard; the real
  difficulty in this chain is reserved for Last Mile's PLC stage (3/3).
- **Hints (if stuck):** 1) "Rootkit's login gets you *onto* the box, not past it - look at what's
  lying around unprotected." 2) "The engineering workstation doesn't answer from outside at all - 
  whatever you need to reach it from has to come from somewhere you already have a shell."
  3) "`/opt/` is a normal place to look for a sysadmin's shortcuts." 4) "You don't have to do this
  from the terminal with curl - your SSH client can forward a port through the box you're already
  in, so you can just point a browser at the login page. Look up SSH **port forwarding** (`ssh -L
  <port>:127.0.0.1:5000 ...`, or the 'Tunnels' tab if you're using PuTTY)."
- **Deps pinned:** `solution/requirements.txt` (`paramiko==3.5.0`).
- **Infra reset:** `docker compose restart` on all three services (Last Mile's PLC included) - a couple seconds, well under 2
  minutes. Full rebuild (`docker compose down -v && docker compose up -d --build`) if an image
  changed.

## Setup / Deployment Notes

**Prerequisites:** Docker + Docker Compose, Python 3.11+ with the pinned deps in
`solution/requirements.txt` (`paramiko`) for the reference solver.

**Deployment: one copy per team (Fargate instance `lateral-drift`).** Lateral Drift and Last
Mile run as one task with one network namespace: `vpn-gateway` (sshd, the only port players can
reach: 22 on the Fargate copy, 2223 locally), `engineering-workstation` (`127.0.0.1:5000`) and Last
Mile's `process-plc` (`127.0.0.1:502` Modbus, `127.0.0.1:8000` status page; its source is in
`src/process_plc/` here so one folder builds the whole copy). Locally, `docker-compose.yml` mirrors
that with `network_mode: service:vpn-gateway`:
```bash
docker compose up -d --build
ssh rootkit@localhost -p 2223
```

**The PLC address the workstation advertises (the Last Mile hand-off).** The Diagnostics panel
and the commissioning sheet print `PROCESS_PLC_HOST:PORT` and the status URL: `127.0.0.1:502` and
`http://127.0.0.1:8000/` by default (`config.py`; the compose passes the same). Whatever string lands
there is what a competitor will tunnel to *through vpn-gateway* (`ssh -L 5020:127.0.0.1:502 ...`),
so it is resolved by the gateway, never by the competitor's laptop, and `127.0.0.1` is right
because the PLC is in the gateway's namespace. Confirm the login dashboard shows a `plc_host` the gateway can `curl`/tunnel to before
calling the chain deployed - a bad hand-off address breaks Last Mile silently, with this
challenge's own flag still solvable.

**Self-reviewed (2026-11-03):** triage 0 FAIL, clean rebuild solved twice (exact flag), stranger
test passed (blind agent, ~9 tool calls, no stalls), README cold-read clean, break-it pass clean
(no sudo/docker access from `rootkit`'s shell, auth correctly gated, wrong creds rejected with no
leak). Difficulty dropped from Hard to Medium based on the stranger test's speed - this
challenge's own checkpoint is intentionally just "reached the workstation," with the harder work
deferred to Last Mile's PLC stage.

**Verified (2026-10-22):**
- Full pivot (SSH -> extract backup -> recover credential -> internal curl -> login) recovers the
  exact flag and the correct Last Mile connection info.
- `engineering-workstation` confirmed unreachable directly (connection refused on its own port
  from outside the compose network - no published port at all). Since 2026-11-05 it listens on
  127.0.0.1 in the gateway's namespace instead (see Deployment above), with the same effect.
- Wrong credentials against the pivot correctly rejected ("Invalid credentials"), no flag leak.

**Reset between contestants:** `docker compose restart` on all three services (a fresh Fargate copy per team at the event) - stateless, no
persistence, a couple seconds.

**Tuning** - credentials and the flag are all in `src/vpn_gateway/eng-sync.conf` and
`src/engineering_workstation/config.py`. If the VPN credential ever changes, keep Know Your
Mark's persona system prompt in sync - this is the one place that pair has to match exactly
across two separate challenges.

## Known Issues / Notes

- The login-bypass mechanism is a straightforward credential check (the recovered second
  credential), not an HTML-comment leak or client-side-only check - those were listed as
  alternates in the original design notes but the backup-tarball credential hunt was already the
  "current lean" and is simpler to verify deterministically. Worth a GM look if a different
  mechanism is wanted.
- `rootkit`'s shell on vpn-gateway has no sudo and no tools beyond what's needed for the intended
  path (`curl`, `tar`, basic coreutils) - deliberately narrow, unlike Blind Spot's attacker box
  which needs broader tooling for its own technique.
