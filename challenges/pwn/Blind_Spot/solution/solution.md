# Blind Spot

**Category:** Pwn
**Difficulty:** Hard
**Author:** Voyager 1

## Description (what the competitor will see)

RazorPower Co.'s habitat ring has a coolant loop controller on Modbus/TCP
at `<challenge-host>:502`, no authentication. Read its holding registers
and you'll find the valve position and coolant flow rate it runs the loop
on; both are writable.

It isn't the only station on that segment. A separate watchdog polls the
controller directly and forces an emergency reset whenever the valve or
flow reading leaves its safe operating band. The watchdog runs no service
of its own and has nothing to log into. It only reads, and it counts a
missed or blocked poll as a fault the same as an out-of-range one, so
blinding it or cutting its link to the controller gets you nowhere: the
controller won't release anything unless the watchdog is actively
reporting good readings the whole time.

Push the loop outside its safe band and hold it there long enough for the
controller to react, without the watchdog ever reading a bad value off
the wire.

ARP spoofing only works from the same segment as the controller and the
watchdog, so the challenge includes a jump box that already sits on it:

```
ssh player@<challenge-host> -p 2222
password: bl1ndsp0t
```

## Files Provided

- None — everything you need is reachable live from the jump box on the
  provided network segment (`10.13.37.0/24`).

## Flag

`flag{the_monitor_saw_nothing}`

## Solution

1. Player SSHes into the provided jump box (`attacker`, 10.13.37.99 —
   already on the same segment) and enumerates it, finding two more
   hosts: `controller` (10.13.37.10, Modbus/TCP, unit ID `0x01`) and
   `monitor` (10.13.37.20, no listening service — it's a client, not a
   server).
2. Player connects directly to `controller` and reads holding registers
   0-1: `valve_position` (%) and `flow_rate` (L/s). Writing an unsafe
   value directly is easy — but `monitor` polls the same two registers
   every 2 seconds. If it ever reads a value above the safe thresholds
   (`valve_position > 40` or `flow_rate > 500`), or the poll itself fails
   or times out, it writes `0x00F0` to register 50 (`LOCKDOWN`), which
   snaps the controller back to safe defaults, **and** separately reports
   its verdict to `controller` over `mgmt_net` (a private link `attacker`
   has no interface on at all — see "Why `mgmt_net` exists" below). A
   naive "ARP-poison and blackhole everything" MITM — dropping all
   `monitor`↔`controller` traffic instead of relaying it — does *not*
   work: `monitor` still can't reach `controller` to poll, so it reports
   `ALARM` over the unspoofable `mgmt_net` link every cycle, and
   `controller`'s flag-unlock logic gates on that report, not on whether
   the (spoofable) lockdown write arrived.
3. The intended technique: ARP-poison both `controller` and `monitor` so
   traffic between them detours through the player's box (`arpspoof`/
   `scapy`), enable IP forwarding, and use an `iptables` `PREROUTING`
   `REDIRECT` rule to funnel the intercepted TCP session into a local
   proxy.
4. The proxy forwards `monitor`'s read requests to the real controller
   untouched, but rewrites the FC03 response payload — splicing in safe
   `valve_position`/`flow_rate` values — before forwarding it back to
   `monitor`. `monitor` never sees anything but nominal readings, so on
   `mgmt_net` it keeps reporting `SAFE` every cycle, same as always.
5. Meanwhile, the player writes the real unsafe values directly to
   `controller` over their own (unintercepted) connection — their own
   traffic to the controller was never part of the poisoned link.
6. `controller` tracks how long its registers have stayed continuously
   unsafe *and* how long `monitor`'s `mgmt_net` heartbeat has stayed
   `SAFE` and recent (no gap over 5s). Once both conditions hold for the
   full 20-second grace period, it unlocks holding registers 100+ with
   the flag, one ASCII character per register, which the player reads
   back directly.

### Why `mgmt_net` exists (a real bug this challenge shipped with, briefly)

The first working version of this challenge gated the flag purely on
whether `controller` ever received the plant_net `LOCKDOWN` write —
i.e., detection was entirely mediated by a message traveling over the
same segment the player already controls. Testing found the obvious
consequence: ARP-poisoning both hosts and then just **dropping** all
traffic between them (via an `iptables … -j DROP`, no relay, no
response-rewriting proxy at all) also won, because it silenced the
lockdown write along with everything else `monitor` tried to send.
That's strictly easier than the intended solve and defeats the point of
the challenge.

The fix adds `mgmt_net` — a second, `internal: true` Docker network
between `controller` and `monitor` only. `attacker` has no interface on
it and no route to it (verified: a direct connection attempt from the
jump box to `10.13.38.10:9999` just times out — there's nothing to
ARP-poison or blackhole, because the jump box was never given an
interface there via docker-compose in the first place). `monitor`
reports its real per-cycle verdict (`SAFE`/`ALARM`) there, and
`controller`'s flag logic in `src/controller/server.py`
(`_watchdog_currently_pacified`) requires that report to be recent
and `SAFE` throughout the grace window — not just "no lockdown write
arrived." Verified experimentally post-fix: the same ARP-poison+DROP
approach now leaves the flag registers all zero, while the intended
ARP+relay+rewrite solve still works unchanged (`monitor` still sees and
reports `SAFE` throughout, since the proxy keeps feeding it safe reads).

## Solve Script

See `solution/solve.py` — implements the full chain: ARP poisoning,
`iptables` redirect, a rewriting Modbus proxy, the direct tamper write,
and the final flag read.

```bash
ssh player@<challenge-host> -p 2222   # password: bl1ndsp0t
# copy or re-create solve.py on the jump box, then:
sudo python3 solve.py
```

`solve.py` uses `IFACE = "eth0"`, which is correct as-is when run from
inside the `attacker` container (its only interface). Requires root
(raw ARP frames, `iptables`, `sysctl`) — the jump box's `player` user has
passwordless `sudo` and the container has `NET_ADMIN`/`NET_RAW`
capabilities for exactly this. Running it from the GM's own host instead
of the jump box only works if that host has genuine L2 adjacency to
`plant_net`, which a plain Docker Desktop VM (macOS/Windows) does not
have — the jump box exists so this doesn't matter for contestants.

Expected output ends with:

```
FLAG -> flag{the_monitor_saw_nothing}
```

## Techniques / Tags

`arp-spoofing`, `mitm`, `modbus`, `traffic-manipulation`, `live-process`

## Setup / Deployment Notes

```bash
docker compose up -d --build
```

Three services come up on `10.13.37.0/24` (`plant_net`); `controller` and
`monitor` additionally share a private `10.13.38.0/24` (`mgmt_net`) that
`attacker` is not attached to:

- `controller` (10.13.37.10 / 10.13.38.10) — the coolant loop's
  Modbus/TCP interface, port 502, plus a heartbeat listener on
  `10.13.38.10:9999` reachable only via `mgmt_net`.
- `monitor` (10.13.37.20 / 10.13.38.20) — the watchdog. It has no
  listening port on `plant_net`; it's a Modbus/TCP *client* that polls
  `controller` every 2 seconds, writes a lockdown code if anything looks
  wrong (including a failed poll), and separately reports its real
  verdict to `controller`'s heartbeat listener over `mgmt_net`. It only
  shows up in `plant_net` traffic and container logs (`docker compose
  logs -f monitor`).
- `attacker` (10.13.37.99) — the jump box. `ssh` (port 2222 on the host)
  is the only thing exposed to contestants; it's a disposable box scoped
  to this challenge's own segment, with `NET_ADMIN`/`NET_RAW` capabilities
  and a passwordless-sudo `player` user so the ARP-spoofing + `iptables`
  technique works out of the box. It has no interface on `mgmt_net` and
  no route to it. Comes with `arpspoof` (dsniff), `nmap`, `tcpdump`,
  `nano`, and Python with `scapy`/`pymodbus` preinstalled — the goal is
  for the challenge's difficulty to come from figuring out and chaining
  the technique, not from fighting the environment (missing editor, no
  scanner, hand-rolling ARP packets from scratch). `iptables`/`sysctl`
  binaries live in `/sbin`, which isn't on the interactive login `PATH`
  by default — that's fine, `sudo`'s `secure_path` covers it, so
  `sudo iptables ...` / `sudo arpspoof ...` just work without contestants
  needing to know why bare `iptables` "isn't found."

Give contestants only the challenge host, the jump box's SSH port
(2222), and its credentials (`player` / `bl1ndsp0t` — change this before
a real event if you want a per-team credential instead of a shared one).
Do **not** hand out `controller`'s or `monitor`'s IPs directly —
discovering them (ARP scan / traffic observation from the jump box) is
part of the challenge.

**Why the jump box exists:** ARP spoofing only works if the attacker can
put frames on the same broadcast domain as `controller` and `monitor`. A
contestant's own laptop, connecting through a normal forwarded port, is
never actually on that segment — only IP-routed to it at best. Rather
than requiring venue infra to put contestants' own machines on the wire
(macvlan bound to a physical VLAN, or a bridged/TAP-mode VPN), `attacker`
is pre-attached to `plant_net` so contestants get genuine L2 adjacency
for free, regardless of what network or OS they're connecting from.

To reset between contestants: `docker compose restart`. `lockdown_count`
and `_flag_unlocked` are in-memory only and reset on restart. Restarting
`attacker` also clears any ARP-poisoning state or iptables rules a prior
contestant left behind — do this between teams if reusing one deployment.

## Known Issues / Notes

- `GRACE_SECONDS = 20` and the 2-second poll interval are tuned for fast
  iteration/testing. Consider raising `GRACE_SECONDS` in
  `src/controller/server.py` for the live competition so a lucky single
  missed poll (e.g. transient network jitter) doesn't gift the flag —
  20s survives roughly 10 consecutive polls, which is already unlikely
  by accident, but tune to taste.
- The FC03 response rewrite in `solve.py` assumes `monitor` always reads
  exactly registers 0-1 in one request (`byte_count == 4`). That matches
  `src/monitor/watchdog.py` as written; if the poll shape changes, the
  proxy's rewrite condition needs to change with it.
- Because `monitor` opens a brand-new TCP connection every poll (rather
  than keeping one alive), the intended proxy technique never has to
  deal with TCP sequence-number continuity across a hijacked existing
  session — it only ever proxies fresh, complete connections. This was
  a deliberate simplification to keep the challenge's core lesson
  (ARP MITM + in-flight telemetry forgery) front and center rather than
  making it also a TCP-hijacking challenge.
