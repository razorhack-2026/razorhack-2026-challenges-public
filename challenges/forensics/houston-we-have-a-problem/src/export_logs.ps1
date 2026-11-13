New-Item -ItemType Directory -Force -Path "C:\Temp\export" | Out-Null

wevtutil epl "Security" "C:\Temp\export\Security.evtx" /ow:true
wevtutil epl "Microsoft-Windows-Sysmon/Operational" "C:\Temp\export\Microsoft-Windows-Sysmon-Operational.evtx" /ow:true
wevtutil epl "Microsoft-Windows-PowerShell/Operational" "C:\Temp\export\Microsoft-Windows-PowerShell-Operational.evtx" /ow:true

Write-Host "--- Export results ---"
Get-ChildItem "C:\Temp\export" | Format-Table Name,Length
