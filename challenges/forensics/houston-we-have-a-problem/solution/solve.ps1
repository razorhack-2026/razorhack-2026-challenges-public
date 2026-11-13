<#
Houston, We Have a Problem: reference solver (GM-only).

Reads only the competitor files in dist/ and prints the flag. Nothing is hardcoded:
the account, ciphertext, C2 host and key all come from the logs.

  1. Security 4624 with LogonType 10 names the RDP intruder account.
  2. Sysmon Event 1 for that account with -enc is the beacon; decode it (UTF-16LE).
  3. Sysmon Event 13 Run value whose decoded -enc posts to the same C2 host carries the key.
  4. base64-decode the ciphertext and XOR it with the repeating key.

Windows only (Get-WinEvent reads .evtx): Windows PowerShell 5.1 or PowerShell 7.
Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File solution\solve.ps1 [-Dist <dir>]
Progress goes to the host; the flag is the only thing written to the output stream.
#>
param([string]$Dist = (Join-Path $PSScriptRoot '..\dist'))
$ErrorActionPreference = 'Stop'

# EventData as a hashtable. XML, so it works without the Sysmon provider manifest installed.
function Get-EventData($evt) {
    $x = ([xml]$evt.ToXml()).Event
    $h = @{ Time = $x.System.TimeCreated.SystemTime }
    foreach ($d in $x.EventData.Data) { if ($d.Name) { $h[$d.Name] = $d.'#text' } }
    $h
}

# -EncodedCommand is base64 of UTF-16LE text.
function ConvertFrom-EncodedCommand([string]$text) {
    $m = [regex]::Match([string]$text, '(?i)\s-enc\s+([A-Za-z0-9+/=]+)')
    if (-not $m.Success) { return $null }
    [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($m.Groups[1].Value))
}

function Get-Records([string]$file, [int]$id) {
    Get-WinEvent -Path (Join-Path $Dist $file) -FilterXPath "*[System[EventID=$id]]" |
        ForEach-Object { Get-EventData $_ }
}

# 1. The RDP account.
$rdp = @(Get-Records 'Security.evtx' 4624 | Where-Object { $_.LogonType -eq '10' })
$accounts = @($rdp | ForEach-Object { $_.TargetUserName } | Sort-Object -Unique)
if ($accounts.Count -ne 1) { throw "Expected one RDP account, found: $($accounts -join ', ')" }
$account = $accounts[0]
$sources = @($rdp | ForEach-Object { $_.IpAddress } | Sort-Object -Unique) -join ', '
Write-Host "[1] $($rdp.Count) RDP logon(s) as $account from $sources"

# 2. That account's encoded PowerShell: the beacon.
$sysmon = 'Microsoft-Windows-Sysmon-Operational.evtx'
$beacons = @(Get-Records $sysmon 1 |
    Where-Object { $_.User -like "*\$account" } |
    ForEach-Object { ConvertFrom-EncodedCommand $_.CommandLine } |
    Where-Object { $_ })
if ($beacons.Count -ne 1) { throw "Expected one encoded command run as $account, found $($beacons.Count)" }
$beacon = $beacons[0]
$ciphertext = [regex]::Match($beacon, "\`$\w+\s*=\s*'([A-Za-z0-9+/=]+)'").Groups[1].Value
$c2 = [regex]::Match($beacon, 'https?://([^/\s]+)/').Groups[1].Value
if (-not $ciphertext -or -not $c2) { throw "Beacon body not in the expected shape: $beacon" }
Write-Host "[2] beacon decoded: posts a base64 value to $c2"

# 3. The Run-key persistence that talks to the same C2 host carries the key.
$keys = @(Get-Records $sysmon 13 |
    Where-Object { $_.TargetObject -match '\\CurrentVersion\\Run\\' } |
    ForEach-Object { ConvertFrom-EncodedCommand $_.Details } |
    Where-Object { $_ -and $_.Contains("//$c2/") })
if ($keys.Count -ne 1) { throw "Expected one Run value posting to $c2, found $($keys.Count)" }
$key = [regex]::Match($keys[0], "\`$\w+\s*=\s*'([^']+)'").Groups[1].Value
if (-not $key) { throw "Run value body not in the expected shape: $($keys[0])" }
Write-Host "[3] key recovered from the Run value ($($key.Length) chars)"

# 4. Repeating-key XOR.
$ct = [Convert]::FromBase64String($ciphertext)
$kb = [Text.Encoding]::ASCII.GetBytes($key)
$pt = New-Object byte[] $ct.Length
for ($i = 0; $i -lt $ct.Length; $i++) { $pt[$i] = $ct[$i] -bxor $kb[$i % $kb.Length] }
Write-Host '[4] flag:'
[Text.Encoding]::ASCII.GetString($pt)
