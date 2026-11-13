# First Boot — build notes (GM-only, never ships)

The artifacts come from a real session on a throwaway Windows 11 Pro VM (Proxmox VM 404
`winlab`, homelab host), not hand-synthesized hives. Everything below runs from the Proxmox host
over SSH. The VM is driven with `qm sendkey` + `qm monitor` (no NIC, no guest agent).

## Files

| Path | Role |
|---|---|
| `tool/crew_setup.cs` | The helper's tool (C# 5, built in-VM with the .NET Framework `csc.exe`) |
| `vm/autounattend.xml` | Unattended install: offline, local `trainee` (no password, auto-logon), `KOT-WSM-117` |
| `vm/make_profile.py` | Splits the flag from `challenge.yml` into the profile's contents (head, Base64) and filename (tail, hex) |
| `vm/build.ps1` | Build phase only: compiles `crew_setup.exe` onto the stick, copies the profile and `README.txt` |
| `vm/README.txt` | Story file on the stick |
| `vm/vmtype.py` | Types a string into the VM console via `qm sendkey` |
| `vm/scenario.sh` | Replays the onboarding session from the `clean` snapshot, then a full shutdown |
| `vm/collect.sh` | Maps the stopped VM's disk read-only (BitLocker clear-key via dislocker) and zips the pack |

## VM

Win11 Pro x64 (Microsoft ISO `Win11_x64_en-us.iso`, build 26300, SHA-256 checked against
Microsoft's published hash), q35 + OVMF (pre-enrolled keys, 2023 certs) + TPM 2.0, 4 vCPU,
6 GB, 64 GB SATA SSD, **no network device**, two IDE CD drives (so the stick lands on `F:`).
Snapshots: `installed` (after first logon, before the compile) → `clean` (scenario start).

## Rebuild (e.g. after a flag change)

1. Edit the flag in `challenge.yml`. The split marker is `_st3p_` (see `make_profile.py`).
2. `python3 src/vm/make_profile.py <setup_dir>`, copy `crew_setup.cs`, `build.ps1`,
   `README.txt` and `autounattend.xml` into `<setup_dir>`, then on the host
   `genisoimage -J -r -V FBSETUP -o /var/lib/vz/template/iso/fbsetup.iso <setup_dir>`.
3. Stick: a fresh 64 MB MBR FAT32 image labelled `ONBOARD` (made on macOS with
   `hdiutil create -size 64m -fs "MS-DOS FAT32" -volname ONBOARD -layout MBRSPUD`, converted to
   raw with `hdiutil convert -format UDTO`).
4. Build phase: `qm rollback 404 installed`, attach `fbsetup.iso` on `ide0`, start, hot-plug the
   stick (`drive_add` + `device_add usb-storage,...,bus=ehci.0,port=2`), Win+R
   `powershell -noexit -ep bypass -f D:\build.ps1` → `BUILD OK`. Unplug, `qm stop`.
5. Copy the built stick image aside, `qm rollback 404 installed` (this discards csc.exe and
   build.ps1 traces), set `ide0` to an empty CD, `qm snapshot 404 clean`.
6. `scenario.sh <built-stick.img>` (~10 min), then `collect.sh <out_dir>`.
7. Copy `first-boot-artifacts.zip` to `dist/`, run `solution/solve.py`, and re-run the leak scan
   (no `flag{`, ASCII or UTF-16, in any file).

## Gotchas hit on the 2026-11-04 build

- **Product key page.** Without a `<ProductKey>` the multi-edition ISO stops at the key page,
  and WinPE ignored `qm sendkey`/tablet input there. The answer file now carries Microsoft's
  published generic Pro install key (edition selection only, no activation).
- **No `<Password>` element → "password must be changed".** At first logon, OK then submit the
  three fields blank; the account stays passwordless. Keyboard input works in the full OS.
- **BitLocker device encryption turns itself on** (vTPM present, no Microsoft account). The
  volume keeps a clear-key protector, so `dislocker-fuse -r -c` opens it read-only on the host
  (`apt install dislocker`); `collect.sh` handles this.
- **`ntfs3` is case-sensitive:** Amcache lives under `Windows\appcompat\Programs`.
- **One unreadable prefetch** (`CTFMON.EXE`) came back as noise through the offline unlock
  (not in an FVE metadata region; cause not found). `collect.sh` drops any `.pf` without the
  `MAM` header and logs it.
- **The vault's secret hook** flags the `publicKeyToken` attribute (Microsoft's fixed public
  component token, required on every unattend `<component>`) as a credential. False positive.
  `autounattend.xml` was written via shell with Andy Roid's approval.
- **`qm monitor` `mouse_move` takes screen pixels** for the absolute USB tablet, not 0–32767.
