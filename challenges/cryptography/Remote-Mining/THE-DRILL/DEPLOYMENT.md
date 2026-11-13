# THE-DRILL: Deployment Guide

THE-DRILL is the SSH server for the KALIUM mining challenge. It runs in Docker and hosts the three Drill Containment Units (Termite-01, Dog-02, Mole-03). Teams SSH in and use the `dcu` Access Console to reach the units.

Run every command in this guide from the challenge folder, `challenges/cryptography/Remote-Mining/`, unless it says otherwise. File paths below are relative to it.

**Units and PRs.** The server lives in the Remote Mining folder because Termite-01 is the first level. The image includes whichever unit files are in `src/`: `crypto.py` (Termite-01) ships with Remote Mining, and the Dog-02 and Mole-03 PRs add `src/crypto_level2.py` and `src/crypto_level3.py`. Until a unit's file is there, it shows as `[OFFLINE]` in the console.

---

## 1. The two deployments

There are two separate deployments. Each has its own compose file, port and saved progress, and they can run at the same time.

| | Production | Dev |
|---|---|---|
| Compose file | `docker-compose.yml` | `docker-compose.dev.yml` |
| Port | `2222`, open to the network | `2223`, **this machine only** |
| Accounts | `THE-DRILL/teams.txt` | `THE-DRILL/teams.txt` **plus** `THE-DRILL/dev/teams.txt` |
| Cheat code | Does not exist | Works for `THE-DRILL/dev/teams.txt` accounts only |
| Progress volume | `the-drill_dcu-progress` | `the-drill-dev_dcu-progress` |
| Command prefix | `docker compose …` | `docker compose -f docker-compose.dev.yml …` |

The dev deployment is the production image plus the `THE-DRILL/dev/` folder, which is mounted when the container starts. The production image never contains the dev accounts or the cheat code: `.dockerignore` keeps `THE-DRILL/dev/` out of the build. Production has no configuration that would enable the cheat, and the dev accounts don't exist there.

**Dev accounts and the cheat code**
- `THE-DRILL/dev/teams.txt` holds the dev accounts (currently `TEAM#AA` and `TEAM#BB`), one `USERNAME:PASSWORD` per line.
- `THE-DRILL/dev/code.txt` holds the cheat code on its first line (currently `uuddlrlrba`). Typing it at the console menu toggles "all units unlocked" for that dev account. The units show `(DEV)` while it's on, and real progress is never marked as solved.
- Inside the dev container, `THE-DRILL/dev/` is mounted under `/root`, so teams can't read it. The cheat is checked by the unit processes, not by the `dcu` console (which any team can read).
- Dev solves in Mole-03 only count on the **dev** scoreboard.

---

## 2. Files that matter

| File | What it is | Rebuild needed after editing? |
|---|---|---|
| `THE-DRILL/teams.txt` | Production team accounts (`USERNAME:PASSWORD`) | Yes |
| `THE-DRILL/dev/teams.txt`, `THE-DRILL/dev/code.txt` | Dev accounts and cheat code | Restart the dev deployment (`up -d --force-recreate`) |
| `src/crypto.py`, `src/crypto_level2.py`, `src/crypto_level3.py` | The three units: settings, flags, story text. Levels 2 and 3 arrive with their own PRs | Yes |
| `THE-DRILL/motd` | Login screen (story text) | Yes |
| `THE-DRILL/sshd_config` | SSH server settings | Yes |
| `THE-DRILL/host_keys/` | The server's SSH identity (see §4) | Don't edit; created automatically |
| `docker-compose.yml`, `docker-compose.dev.yml` | Ports, time zone, volumes | Run `up -d` again |

"Rebuild" means `docker compose up -d --build`. It rebuilds the image and recreates the container, **keeping progress** (§5).

The solve scripts in `solution/` never go onto the server. `.dockerignore` only lets `src/` and `THE-DRILL/` into the build, and `.gitignore` keeps `THE-DRILL/host_keys/` out of git.

---

## 3. Deploying

### Prerequisites
- Docker with the Compose plugin. The Docker service must be running: `sudo systemctl start docker`.
- The `docker-buildx` plugin is optional. Without it you'll see a "requires buildx plugin" warning, which is harmless.

### First deployment, or a clean start for the event
```bash
docker compose down -v            # wipes production progress, scores and round history
docker compose up -d --build
docker compose logs -f            # wait for "Server listening on 0.0.0.0 port 22", then Ctrl+C
```

### How players connect
```bash
ssh -p 2222 'TEAM#01@<server-ip>'
```
- Quote the username, because `#` starts a comment in most shells.
- `<server-ip>` is the address of the machine running Docker on the event network. On this machine, `ip -4 addr` lists it, for example `XXX.XXX.0.XX`.
- Port 2222 is open on every network interface. If the host has a firewall, it must allow TCP 2222.
- To use another port, change `"2222:22"` in `docker-compose.yml` (e.g. `"22:22"`), then run `docker compose up -d`.

### Dev deployment
```bash
docker compose -f docker-compose.dev.yml up -d --build
ssh -p 2223 'TEAM#AA@localhost'
```
The dev server only accepts connections from the machine it runs on. To reach it from another machine, use an SSH tunnel to the host rather than opening the port.

### Time zone
Mole-03 releases blocks on the hour and the half hour, shown in the container's local time. The default is `America/Chicago`. To use another zone, set it when starting:
```bash
TZ=America/New_York docker compose up -d
```
The time zone is applied when the container is created, so recreate the container (`up -d` with a new `TZ` does this).

---

## 4. SSH host keys

**What they are:** host keys are the server's identity. The first time a player connects, their SSH client saves the server's key in `~/.ssh/known_hosts`. Each later connection checks the server against the saved key.

**Where they live:** `THE-DRILL/host_keys/` on the Docker machine, mounted into the container. They're created on the first start and reused after that. As a result:
- Rebuilds, `down`, and `down -v` **don't** change the server's identity.
- Production and dev share the same keys.

**If a player sees `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`:** the key they saved doesn't match the server. This happens if `THE-DRILL/host_keys/` was deleted, if they connected to a different server at the same address and port before, or if they connected to an earlier version of THE-DRILL that created new keys on each start. If you know the server is genuine, they clear the old entry and reconnect:
```bash
ssh-keygen -R '[<server-ip>]:2222'
```
For `localhost`, use `'[localhost]:2222'`. The brackets are required for non-standard ports.

**Letting players verify the server:** you can post the fingerprint where players can see it:
```bash
ssh-keygen -lf THE-DRILL/host_keys/ssh_host_ed25519_key.pub
```
On first connect, players compare it with the `ED25519 key fingerprint is SHA256:…` line their client shows.

**Handling the folder:**
- **Owner:** `THE-DRILL/host_keys/` is owned by root because the container creates it, so use `sudo` to copy or remove it.
- **Backing up or moving servers:** `sudo cp -a THE-DRILL/host_keys /somewhere/safe`. Copy `THE-DRILL/host_keys/` to the new machine to keep the same identity there.
- **Rotating the keys** (only if they leak): `sudo rm -r THE-DRILL/host_keys`, then `docker compose restart`. Every player then gets the warning above once.
- **Keep it private:** never commit `THE-DRILL/host_keys/` (`.gitignore` already excludes it). Anyone with the private keys could pose as the server.

---

## 5. Progress and resetting

**What's saved:** all progress lives in the deployment's Docker volume, mounted at `/var/lib/dcu`:
- `<TEAM>/unit1.mined` and `unit2.mined` record each team's Termite-01 and Dog-02 solves.
- `<TEAM>/dev.unlocked` is the cheat toggle (dev deployment only).
- `unit3.json` holds Mole-03's scores, team colors, round history, and the current block and its answer.

| Goal | Command | Progress |
|---|---|---|
| Apply edited code, flags, `THE-DRILL/teams.txt` or `THE-DRILL/motd` | `docker compose up -d --build` | Kept |
| Restart the server | `docker compose restart` | Kept |
| Stop the server | `docker compose down` | Kept |
| **Full reset** (everything, all teams) | `docker compose down -v && docker compose up -d` | **Wiped** |
| Reset one team's Termite-01 and Dog-02 | `docker compose exec the-drill rm -r '/var/lib/dcu/TEAM#05'` | That team's unit 1–2 progress |
| Reset only Mole-03 (scores and rounds) | See below | Mole-03 only |

Use the dev compose file (`docker compose -f docker-compose.dev.yml …`) to do the same on the dev deployment. Its volume is separate, so resetting one never affects the other.

**Reset only Mole-03.** This procedure is untested. Stop the server first, because Mole-03 keeps its state in memory and would write the file back:
```bash
docker compose stop
docker compose run --rm -T the-drill rm -f /var/lib/dcu/unit3.json
docker compose start
```

**Not supported:** changing or removing one team's Mole-03 score. Use the full reset or the Mole-03 reset instead.

**Notes on resetting and Mole-03 settings:**
- **Removing a team:** take it out of `THE-DRILL/teams.txt` and rebuild. That deletes the account, but its saved progress, and its Mole-03 score on the scoreboard, stay until a reset.
- **Changing Mole-03's `NONCE_LENGTH` or `ROUND_SECONDS`:** the change applies from the next block. The block that's live during the rebuild was made with the old settings and may be unsolvable until it expires. A full or Mole-03 reset avoids this.

---

## 6. Accounts and passwords

- **Production accounts:** `THE-DRILL/teams.txt`, one `USERNAME:PASSWORD` per line. Lines starting with `#` are ignored. Rebuild after editing.
- **Usernames:** names like `TEAM#07` work.
- **Accounts change on recreate:** they're created each time the container is created. Editing `THE-DRILL/teams.txt` and rebuilding adds, removes or re-passwords them.
- **Root login:** disabled. Only accounts in the `teams` group can log in.
- **Shared passwords:** with every team using `pass`, any team can log in as another. It could then waste that team's guesses (wrong keys lock the whole team out of Mole-03 for 30 seconds) or solve units for them. **Give each team its own password before the event.**

---

## 7. What teams can and can't do

**Can't:**
- Read the challenge code, answers or saved progress (`/opt/dcu` and `/var/lib/dcu` belong to the `drill` service user).
- Read other teams' home folders.
- Read the dev configuration.
- Fake another team's progress: the units identify each connection by its Linux account.
- Tunnel or forward ports through the server.

**Can:**
- See the three `DRILL CONTAINMENT UNIT …` processes, plus active sessions with team names, in `ps`. That's intended flavor, but it shows who's in which unit.
- See other team account names (e.g. with `getent group teams`). The scoreboard shows them anyway.
- Run Python on the server, which the units need. A team could run a miner on the server's CPU. To cap that, add `cpus: "2"` under the service in `docker-compose.yml`.
- Read the `dcu` console's code. It contains nothing secret.

---

## 8. Before the event: checklist

- [ ] `THE-DRILL/teams.txt` lists the real teams, **each with its own password**.
- [ ] Flags are set: `FLAG = "flag{TEMP}"` in `src/crypto.py`, `src/crypto_level2.py` and `src/crypto_level3.py` (once those PRs land).
- [ ] Mole-03's settings are final: `NONCE_LENGTH` (10) and `ROUND_SECONDS` (1800) in `src/crypto_level3.py`.
- [ ] The full reset is done: `docker compose down -v && docker compose up -d --build`.
- [ ] `THE-DRILL/host_keys/` exists and is backed up. Optionally, the fingerprint is posted for players (§4).
- [ ] From another machine on the event network: `ssh -p 2222 'TEAM#01@<server-ip>'` reaches the Access Console.
- [ ] A dev account on port 2222 is refused: `ssh -p 2222 'TEAM#AA@<server-ip>'` should say "Permission denied".
- [ ] The dev deployment is stopped, or runs on the organizer machine only: `docker compose -f docker-compose.dev.yml down`.

---

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Connection refused` | The container isn't running, or the port is wrong. Check `docker compose ps` and `docker compose logs`. The dev deployment is on 2223 and only reachable from its own machine. |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | See §4. Clear the entry with `ssh-keygen -R '[<server-ip>]:2222'`. |
| `Permission denied` at the password prompt | Wrong password, or the account isn't on that deployment. Dev accounts only exist on 2223. |
| `failed to connect to the docker API` | The Docker service isn't running: `sudo systemctl start docker`. |
| `the --chmod option requires BuildKit` | The Dockerfile is an old version. The current one doesn't use `--chmod`. |
| A unit shows `[OFFLINE]` | Its file isn't in `src/` yet (Dog-02 and Mole-03 arrive with their own PRs). Otherwise its process crashed; it restarts itself within a second, and if it stays offline, check `docker compose logs`. |
| Mole-03 rejects a correct-looking answer right after a settings change | The block from before the change is still live (§5). Wait for the next release, or reset Mole-03. |
| The cheat code says "Unknown unit." | You're on production (port 2222), the account isn't in `THE-DRILL/dev/teams.txt`, or `THE-DRILL/dev/` changed without a restart. Run `docker compose -f docker-compose.dev.yml up -d --force-recreate`. |

---

## 10. Running it yourself: two modes

The same image runs two ways, chosen by its environment (`entrypoint.sh`):

| | Single-team copy | Shared server |
|---|---|---|
| Challenges | Remote Mining, High Value Deposit | Employee of the Year - Kalium Collector |
| Units | `DCU_UNITS=1 2` | `DCU_UNITS=3`, `DCU_UNGATED=3` |
| Passwords | `TEAM_PASSWORD` for every account, if set | `THE-DRILL/teams.txt`, one per account |
| Progress | Lost when the container is removed | Kept in the `dcu-progress` volume at `/var/lib/dcu` |
| Address | `localhost`, port 2222 (this folder's compose mapping) | `localhost`, port 2222 |

- **Accounts.** `THE-DRILL/teams.txt` in this release holds placeholder accounts
  (`TEAM#01` to `TEAM#03`). Edit it before you rebuild if you host this for other people;
  on a shared server each account's password is all that keeps players apart (see §6).
- **Mole-03 ungated.** With `DCU_UNGATED=3` the server doesn't ask for Dog-02 to be mined first.
- **Reset.** Run the image once with `DCU_RESET_AND_EXIT=1` to empty `/var/lib/dcu`, or
  `docker compose down -v`.
- **Scores.** Mole-03's in-game scoreboard is the record of blocks won.
- **Host keys** are made when the image is built, so every copy has the same identity until the
  next build. `TZ` comes from the environment (`America/Chicago` by default).
