# Poisoned Cache

**Category:** Web
**Difficulty:** Medium
**Author:** Lt. Rico Kopernicus

## Description

Something *really* bad is happening! Our shields just shut down and something foreign is
broadcasting beacon data from our damage control system. I tried to restart the system, 
but it just keeps erroring. Bring our shields back up, track down the beacon, and remove
it - quickly!

Also, just so you know, our shield emitter system only arms with a specific hardware
activation code, don't ask me why. The person who made it left the company decades
ago. All we know is that it's the first 16 hex characters (lowercase) of:

`HMAC-SHA256(key = firmware:key, message = hull:serial + ":" + reactor:seed)`

## Flag

`flag{s3nd_1n_th3_g0ph3r}`

## Solution

The console at `http://<host>:8080` is a monitoring dashboard backed by the ship's
internal state cache. It exposes a "Sensor telemetry uplink" form that fetches any URL
server-side (via libcurl) and echoes the body back - a classic SSRF, and the fetcher
speaks `gopher://`, so it can send arbitrary commands to the internal Redis at
`127.0.0.1:6379`. The flag is **not** in Redis; the console renders it only when ship
state is genuinely healthy, so the cache has to be *repaired*, not just read.

1. **Find out what the state lives in (intended discovery).** The banner says to restart
   the system. The **Danger zone > Restart system** button (with a confirm step) posts to
   `/system/restart`, which fails with a taunt from Dr. Rootkit:
   > "...i hold the write channel to `127.0.0.1:6379` now - your console can read that
   > redis all it likes, but it will never push clean state back..."

   That is the breadcrumb: the state is a **Redis** at `127.0.0.1:6379`, restoring it
   means *writing* to that cache, and the normal write path is severed. The only other
   feature that reaches the internal network is the sensor telemetry fetch (an SSRF) - the
   operator's remaining write primitive. (The taunt also changes as you make progress -
   see Notes.)

2. **Confirm the target.** `http://127.0.0.1:6379/` is a dead end: libcurl waits for an
   HTTP response, Redis answers in its own protocol, and the fetch reports `Empty reply
   from server`. Speak Redis directly over `gopher://` instead - send a `PING`:
   ```
   gopher://127.0.0.1:6379/_PING%0d%0aQUIT%0d%0a
   ```
   The sensor response comes back `+PONG` - that is a Redis instance.

   > The trailing `QUIT` makes Redis close the socket so the reply returns immediately.
   > Without it the console waits out its ~5s read timeout before showing the (same)
   > reply - it still works, just slower.

3. **Dump the inputs over gopher.** Everything after `gopher://host:port/_` is URL-decoded
   and written raw to the socket; Redis accepts inline commands ending in CRLF (`%0d%0a`):
   ```
   gopher://127.0.0.1:6379/_KEYS%20*%0d%0aQUIT%0d%0a
   gopher://127.0.0.1:6379/_GET%20hull:serial%0d%0aQUIT%0d%0a
   gopher://127.0.0.1:6379/_GET%20reactor:seed%0d%0aQUIT%0d%0a
   gopher://127.0.0.1:6379/_GET%20firmware:key%0d%0aQUIT%0d%0a
   ```
   `KEYS *` enumerates everything, including the `rootkit:beacon` key to be evicted.

4. **Compute the activation signature** from the three values, per the brief:
   ```python
   import hmac, hashlib
   activation = hmac.new(firmware_key.encode(),
                         f"{hull_serial}:{reactor_seed}".encode(),
                         hashlib.sha256).hexdigest()[:16]
   ```
   `reactor:seed` is randomised per deploy, so the value differs every run - the
   computation has to actually be performed, not copied from a writeup.

5. **Restore state** - evict the beacon and set the signature in one payload:
   ```
   gopher://127.0.0.1:6379/_DEL%20rootkit:beacon%0d%0aSET%20shield:activation%20<activation>%0d%0aQUIT%0d%0a
   ```

6. **Read the flag.** The ship-state panel auto-refreshes after each telemetry response,
   so as soon as the restore lands it flips to Shield emitters ONLINE, Intruder beacon
   CLEARED, Hull integrity NOMINAL, and reveals the flag - no manual reload:
   `flag{s3nd_1n_th3_g0ph3r}`

Full automated solve: `python3 solution/challenge8_solve.py http://localhost:8080`.

## Notes

- **`file://` is blocked on purpose.** The SSRF fetcher is restricted to
  `gopher`/`http`/`https`. The flag lives in the console process's environment, so an
  arbitrary-file read (`file:///proc/self/environ`) would otherwise hand it over without
  any of the intended work. Keep this restriction when editing the app.
- **The flag is never in Redis.** It is an env var, released only when the console
  recomputes the signature from live cache values and finds the state healthy. A full
  cache dump yields only the activation inputs - the player still has to compute the
  signature and write it back.
- **The restart taunt is progress-aware.** `/system/restart` reads live state and replies
  differently once the beacon is deleted, once the shields are activated, and once the
  ship is fully restored (a plain "System restarted" message). This is flavour only; it
  never writes to Redis.
- **Architecture.** The page lives entirely at `/`; `/telemetry` and `/system/restart` are
  plain-text API endpoints the page calls with `fetch()`. `ctf-console` runs in
  `ctf-redis`'s network namespace (one shared namespace, as in the Fargate task), so the
  console reaches Redis on `127.0.0.1` and Redis binds `127.0.0.1` only: players can reach it
  solely through the console's SSRF.

## Techniques / Tags

`web`, `ssrf`, `gopher`, `redis`