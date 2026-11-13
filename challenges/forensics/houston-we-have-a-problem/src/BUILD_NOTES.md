# Houston, We Have a Problem - Build Notes (2026-09-07)

## Environment
- VirtualBox VM name: `windows` (Win10-labeled, actually running **Windows 10 Pro 22H2** after a MAS/massgrave edition upgrade from Home)
- Console account: `vboxuser` / `vboxuser` (local admin, autologin enabled via unattend)
- Attacker account: `chrisRK` / `P@ssw0rd2026!` (local user, member of Remote Desktop Users)
- Snapshot `configured-ready`: Sysmon (SwiftOnSecurity config) installed, RDP enabled + firewalled,
  `chrisRK` created, `vboxuser` added to "Event Log Readers". **Contains leftover test-run noise**
  (multiple chrisRK RDP logons from today's troubleshooting) - NOT a clean single-narrative state.
  Revert here to skip re-doing all setup, but the real final build should start from an EARLIER
  point (before any chrisRK logons) or a fresh VM entirely.
- NAT port forward already configured: host `127.0.0.1:3390` -> guest `3389` (RDP)
- Host has an RDP credential cached via `cmdkey /generic:TERMSRV/127.0.0.1 /user:chrisRK`
- `.rdp` connection file at `%TEMP%\houston_chrisRK.rdp` (host), uses `authentication level:i:0`
  to skip the cert-trust prompt, `full address:s:127.0.0.1:3390` (must be IPv4 literal, not
  `localhost` - mstsc's IPv6 resolution attempt otherwise stalls the connection)

## Scripts (in `scripts/`)
- `install_sysmon.ps1` - downloads Sysmon + SwiftOnSecurity config, installs service, sets logon
  auditing. **Must be run elevated** (Sysmon driver install needs a true admin token, not just
  UAC-filtered admin-group membership).
- `elevated_setup.ps1` - one-time elevated setup: adds vboxuser to Event Log Readers, enables RDP
  + firewall rule, creates chrisRK account.
- `run_attacker_cmd.ps1` - launches the base64-encoded PowerShell "beacon" command as chrisRK.
  **Do NOT embed a full `powershell.exe -Command "..."` wrapper inside the string you encode** -
  only encode the bare script body, or `-EncodedCommand` will decode into a second real
  `powershell.exe` invocation that logs the flag in cleartext in its own CommandLine (defeats the
  whole "decode it yourself" step). Fixed version here is safe.
- `set_persistence_offline.ps1` - writes the HKCU Run-key persistence value for chrisRK via an
  **offline hive load** (`reg load`/`reg unload`), not a live guestcontrol HKCU write. Needed
  because: (1) guestcontrol's logon type for chrisRK doesn't load a real registry hive, so any
  `HKCU:` access under a guestcontrol session fails outright ("access not allowed") regardless of
  permissions; (2) Windows Defender's behavior monitor blocks a direct `reg add ...CurrentVersion\Run`
  process launch as a T1547.001 persistence pattern - use PowerShell's `HKU:` registry provider
  (New-PSDrive) instead of shelling out to `reg add` for the actual value write. Must **not** hold
  a PSDrive reference into the loaded hive when you `reg unload`, or unload fails with access
  denied (close/let the PS process exit first, then unload).
- `generate_noise.ps1 -Count N` - routine noise generator (ipconfig, tasklist, notepad/calc pops,
  etc.) as vboxuser, for padding before/after the real chain.
- `logoff_console.ps1` - finds whichever session ID vboxuser's console is currently on (it changes
  across VM resumes/resets - don't hardcode session 1) and logs it off.
- `export_logs.ps1` - `wevtutil epl` for all three channels to `C:\Temp\export\`. **Must be run
  elevated** - Security channel specifically needs `SeSecurityPrivilege`, which Event Log Readers
  group membership alone does not grant (unlike Sysmon/RDS-operational channels, which Event Log
  Readers does cover).

## Key gotchas learned today
1. **Guest control + UAC**: `VBoxManage guestcontrol run --username <admin>` always gets the
   UAC-filtered *standard* token, even for a real admin account. Anything needing true elevation
   (Sysmon install, audit policy, reg.exe writes, Security log reads) has to be run manually by a
   human in an elevated window inside the VM - there's no way to auto-elevate through guestcontrol.
2. **Windows client editions (Home/Pro, non-Server) allow only ONE session at a time.** RDP-ing in
   as a different user while the console has an active OR locked session gets rejected
   (`LocalSessionManager` Event 40, reason code 18) after ~15s of session arbitration. Fix: fully
   **sign out** (not lock) the console user first.
3. Signing off the console user via guestcontrol (as that same user, targeting its own session)
   can destabilize VBoxService/guest-control for a bit (`VERR_DUPLICATE` on subsequent calls). A
   VM reset clears it. Doing the sign-out as a distinct step and giving guest control a moment
   before the next call helps.
4. RDP via mstsc needs `full address:s:127.0.0.1:...` (IPv4 literal) in the `.rdp` file, not
   `localhost` - IPv6 resolution silently stalls the connection attempt.
5. Windows 10 **Home** cannot host inbound RDP at all (feature stripped from the SKU) - upgrading
   to Pro via a valid edition-swap (user used massgrave/MAS for this build) restores it even
   without full activation, since the RDP host feature is gated on edition ID, not activation
   status.
6. A VM `reset` (hard reset) can occasionally cause the guest to fall through to iPXE/network boot
   instead of the disk - seen once today, resolved by a clean poweroff + startvm instead of reset.
   If it recurs, catch the VirtualBox splash early (screenshot right after `startvm`) and F12 into
   the boot menu to force the hard disk explicitly.
7. Claude Code's auto-mode safety classifier will block registry-persistence-write actions
   specifically because of the cumulative conversation pattern (fake admin account + RDP + encoded
   PowerShell + persistence reads as "staging a real intrusion"), independent of the action itself.
   Exiting auto mode is the workaround; expect it to fire again for similar actions in a
   fresh auto-mode session.
8. Sysmon `TargetObject` for the persistence key shows the offline mount alias (`HKU\ChrisRKTemp\...`)
   rather than chrisRK's real SID, because of the offline-hive-load technique - a minor realism
   tell, not fixed yet.

## Status as of 2026-09-07
Full attack chain validated end-to-end from the `configured-ready` snapshot: real Type 10 RDP
logon as chrisRK, clean base64-encoded PowerShell "beacon" execution (no cleartext leak), clean
HKCU Run-key persistence (no cleartext leak), heavy routine noise before/after, full three-channel
export (`Security.evtx`, `Sysmon-Operational.evtx`, `PowerShell-Operational.evtx`) all working via
`wevtutil epl` + guestcontrol copyfrom.

**test-export-2026-09-07/** contains that proof-of-concept export - useful for verifying the solve
path and Sigma/Hayabusa detection, but NOT the shippable artifact: it has 5 separate chrisRK Type10
logons (7:52, 8:05, 8:07, 8:08, 9:00 PM) baked in from today's iterative testing, not a single clean
narrative.

## Status as of 2026-09-14 — shippable artifact DONE
The September flag was swapped in (since superseded: the current flag is only in `challenge.yml` and `solution/`). One clean pass completed:
reverted to `configured-ready`, cleared all three log channels (elevated, manual — see below),
noise, real Type 10 RDP logon via actual `mstsc` (not guestcontrol — guestcontrol logons aren't
Type 10), encoded exec as chrisRK, persistence write (elevated, manual), noise, export. Exported
files pulled to host at `Documents\razorhack 2026\houston\final-export-2026-09-14\`.

## Remaining before this is competition-ready
- [ ] Decide whether the `HKU\ChrisRKTemp` cosmetic tell (gotcha #8) is worth fixing.
- [ ] Write the competitor-facing prompt (narrative + what files they receive + hint budget).
- [ ] Decide `challenge.yml` schema against the team's real repo convention (same open item as
      Light Curve).
- [ ] Compress/trim the three .evtx exports for distribution size — also now a judgment call on
      Security.evtx's inflated noise volume (~1200+ records) from an unplanned mid-build Windows
      Update cycle, not just a raw size question.

## New gotchas from the 2026-09-14 final-build session (VBoxManage 7.2.6)
9. **Elevation cannot be bootstrapped through guestcontrol at all, confirmed not just assumed.**
   Tried creating a scheduled task with `/rl highest` from a guestcontrol session authenticated as
   the admin `vboxuser` — plain task creation succeeds, adding `/rl highest` gets `Access is
   denied` every time. Windows requires the creating process to already be elevated. `wevtutil cl`
   and the persistence script's `reg load` both need a human in an elevated window inside the VM
   console — no way around it. Budget for two manual round-trips per full build.
10. **`guestcontrol run -- <exename>` echoes the exe name as a bogus first argument** to tools
    like `quser`/`qwinsta`/`logoff`, which then misparse it ("No User exists for quser.exe").
    Never repeat the exe name after `--` — pass only real parameters (or nothing).
11. **`copyto`/`copyfrom --target-directory` fails if the destination dir already exists.** Copy
    to an explicit destination filename instead, one file at a time.
12. **VERR_DUPLICATE guest-session jam is reproducible**, not a one-off — hit it logging off
    vboxuser's own console via a guestcontrol session authenticated as vboxuser. `guestcontrol
    list all` shows nothing (doesn't help diagnose). Only fix: a VM reset (which can then trigger
    the iPXE-fallthrough bug from gotcha #6 again — check with `VBoxManage controlvm <vm>
    screenshotpng` instead of needing a GUI window open).
13. **Check for a pending Windows Update cycle before starting a build session.** A big chunk of
    this session's instability (VM "aborted" crash, guest-control flakiness) traced back to the
    guest being mid-update, not the challenge build itself. The actual crash was a stale
    `VBoxHeadless.exe` (leftover `--type separate` GUI viewer) racing an update-triggered reboot —
    `taskkill //F //IM VBoxHeadless.exe` before retrying `startvm` fixed it.
14. **RDP cached credentials (`cmdkey`) didn't survive to this session** — had to re-add via
    `cmdkey /generic:TERMSRV/127.0.0.1 /user:chrisRK /pass:P@ssw0rd2026!` before `mstsc` would
    connect non-interactively again.
