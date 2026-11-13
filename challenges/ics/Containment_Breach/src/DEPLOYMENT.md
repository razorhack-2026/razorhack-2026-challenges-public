# Containment Breach — Deployment & Operations (GM only)

GM-only. Not competitor-facing — do not copy into `dist/` or the README. Contains no flag.
Covers how the challenge must be stood up on event infrastructure so it is both solvable and
not trivially bypassable.

## What gets deployed

1. **The simulator** — `docker-compose.yml` in the challenge root (pymodbus). Competitors use the single multi-unit port 5030 (unit IDs 1-3 = Vessels A/B/C, 4 = Cryo Plant), which is the port an instance maps to `{port}`. The per-device ports 502/503/504/505 serve the same datastores and exist for the Ignition gateway; do not hand them to competitors. They listen on 127.0.0.1 only (`DEVICE_HOST` in `src/sim/config.py`), since the gateway shares the sim's network namespace.
   This is what competitors attack.
2. **An Ignition gateway** hosting the `Containment` Perspective project (`src/ignition/`).
   Competitors only need the **read-only Perspective client** URL; the breach popup (and the flag)
   fires there automatically on Vessel C rupture.

**One instance per team.** Starting a team's instance starts both: its own simulator and its own
Ignition gateway, wired to each other (the gateway's device configs point at that instance's
sim on 502/503/504/505). Nothing is shared between teams, so a breach, a griefing write or a
restart only affects the team that caused it, and the flag popup only ever appears in that
team's own HMI. The gateway **is** in the challenge compose: `docker compose up -d` starts the sim, the
gateway and `hmi-proxy` in one network namespace, as in the per-team Fargate task (instance
`containment-breach`), so they reach each other on 127.0.0.1. The gateway image
(`src/ignition/Dockerfile`) is `inductiveautomation/ignition:8.3.9` with the Containment project, the
tags and the four devices (127.0.0.1:502-505) seeded from the files in `src/ignition`, the same files
`containment.gwbk` was built from; the backup itself is no longer used. Tested end to end: the HMI
shows live sim readings and the breach popup appears on Vessel C's rupture. The requirements below
apply to that gateway. Competitors get the HMI as the `HMI` line of the connection info
(`http://<host>:8088/data/perspective/client/Containment`), next to the Modbus `{port}` (5030).

**What competitors can reach.** The gateway itself is not published to them. The `hmi-proxy` service
(nginx, `src/proxy/nginx.conf`) is the competitor-facing port 8088 and passes through only the
Containment project's client page, its websocket and static assets. The gateway web UI and login
(`/web`, `/main`), the config REST API (`/data/api`), other projects such as `Sandbox`, and every other
`/system` path return 404 there. The gateway itself listens on 8089 (and the gateway network on
8060). Ignition can't be made to listen on loopback only, and on Fargate every listening port is
reachable by the team, so a team that scans can find it; its admin password is random for each start
and never stored (`src/ignition/rh-entrypoint.sh`), so there is no login to use. Locally the compose
publishes 8089 on the host's loopback only. Checked against a live stack: all of those paths 404
through the proxy, and the HMI still works end to end.

**The flag is not in the client before the breach.** From a clean sim, the flag text was in none of the
page HTML, HTTP responses or websocket messages before Vessel C ruptured, and appeared in the page only
after. Opening the popup view by URL (`/breach-popup`, `/ContainmentBreachPopup`, `?view=...`) shows
"View Not Found". The popup is opened by the gateway when the breach tag flips and is never present in
the client until then. If you change the project, re-run that check from a freshly restarted sim.

Rebuilding `containment.gwbk` after changing anything under `src/ignition/`: create a throwaway Ignition
Lab gateway, `gw.ps1 apply <gateway> src/ignition`, then `gwcmd.sh -b containment.gwbk` inside its
container. The backup still carries the lab template's admin login (`admin` / `1qaz@WSX`), so never
run a gateway restored from it where competitors can reach it. The images don't use it: they build
from the files under `src/ignition` directly, so rebuilding the backup isn't needed for the event.

## Gateway login hardening (required)

The flag string is a static label inside the gateway project (`ContainmentBreachPopup`). Anyone
who can authenticate to the gateway's **config pages or launch a Designer** can open that view and
read the flag without solving the challenge. Therefore (the gateway image does the first two:
`rh-entrypoint.sh` sets a random admin password at each start, and it is never restored from the
backup):

- **Do not deploy with the dev-default credentials** (`admin` / `1qaz@WSX`). Those are the Ignition
  Lab convention for throwaway local gateways and are public knowledge. Set a **strong, unique
  admin password** at deploy time (generated, 20+ chars), stored in the event's secret store —
  **never** in this repo, a backup committed here, or a challenge file.
- If the gateway is cloned from a `.gwbk`/template that carries the dev password, **rotate the
  admin password after restore** and before the gateway is reachable by competitors.
- **Expose only the Perspective client.** Competitors should reach the HMI page and nothing else.
  Block/do-not-publish to the competitor network: the gateway config/status pages, the Designer
  download + launch endpoint, and the config REST API. A strong password is defense-in-depth; the
  admin surface should not be reachable from the player network at all.
- Keep every project tag **Read-Only** (already the case) and confirm the HMI has no input/write
  components — the attack path is Modbus to the sim, never the HMI.

Quick verification before go-live:
- The Perspective client URL loads the HMI with **no login prompt**.
- The gateway config/login page is **not reachable** from the competitor network (or at minimum
  rejects the old `admin`/`1qaz@WSX`).
- The flag does not appear anywhere in the client until Vessel C breaches.

## Trial-expiry contingency (prepare before the event)

**Note for infra: every team's Ignition gateway must be reset at least every 2 hours.** The trial
lasts about two hours per gateway and a plain restart does not reset it. Handled in the image: each
start is a fresh gateway with a fresh trial, and `rh-entrypoint.sh`'s trial keeper resets the trial
through the gateway's own API once it expires (the same keeper as the ECLSS gateway). Locally,
`docker compose up -d --force-recreate ignition` also gives a fresh gateway. A reset drops open HMI
sessions, so players reload the page; the sim and the breach state are separate and unaffected. A
licensed gateway removes the need entirely.

**Problem:** an unlicensed Ignition gateway runs in **trial mode for ~2 hours**, after which
Perspective sessions and the Designer stop until the trial is reset from the gateway config page.
A restart does **not** reset the clock. A CTF runs far longer than 2 h, so a trial gateway **will
expire mid-competition** and take the HMI (and the flag reveal) down with it.

Have one of these in place and tested before the event:

1. **Preferred — run a licensed gateway.** Activate a Standard (or Edge) license on the event
   gateway so there is no trial clock at all. This is the only option with no moving parts during
   the competition.
2. **Fallback — automated trial reset / reprovision.** If no license is available, script a
   reset on a <2 h cadence (a watchdog that either resets the trial via the gateway config, or
   tears down and recreates the gateway from a saved `.gwbk` and re-applies `src/ignition/`).
   Note resetting the trial requires the admin login, so the watchdog must hold the hardened
   credential securely. Recreating the gateway is the clean reset; a plain restart is not.
3. **Operational safety net.** Keep a spare pre-provisioned gateway ready to swap in, and monitor
   the Perspective client (synthetic check) so an expiry is caught in seconds, not by a player
   ticket. Ensure the **sim is independent** of the gateway (it is — separate compose) so only the
   gateway needs attention.

Whichever path: do a **full-duration dry run** (longer than 2 h) that confirms the HMI, the breach
popup, and the sim all survive, and that a gateway swap/reset re-applies the project cleanly and
re-fires the popup on a fresh breach.
