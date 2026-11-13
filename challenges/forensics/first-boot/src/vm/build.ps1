# build.ps1 -- BUILD PHASE ONLY. Runs on the VM from the setup disc, then the VM is
# rolled back to the `installed` snapshot, so csc.exe and this script leave no trace
# in the shipped artifacts. Compiles crew_setup.exe onto the ONBOARD stick and copies
# the calibration profile next to it.
$ErrorActionPreference = 'Stop'

$stick = ([IO.DriveInfo]::GetDrives() | Where-Object { $_.IsReady -and $_.VolumeLabel -eq 'ONBOARD' }).RootDirectory.FullName
if (-not $stick) { throw 'ONBOARD stick not found' }

$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
& $csc /nologo /target:exe /out:"$stick\crew_setup.exe" "$PSScriptRoot\crew_setup.cs"
if ($LASTEXITCODE -ne 0) { throw "csc failed ($LASTEXITCODE)" }

New-Item -ItemType Directory -Force "$stick\profiles" | Out-Null
Copy-Item "$PSScriptRoot\profiles\*.cal" "$stick\profiles\"
Copy-Item "$PSScriptRoot\README.txt" $stick

Get-ChildItem -Recurse $stick | Format-Table FullName, Length -AutoSize
Write-Host 'BUILD OK'
