$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path C:\Temp | Out-Null

Write-Host "Downloading Sysmon..."
Invoke-WebRequest -Uri "https://download.sysinternals.com/files/Sysmon.zip" -OutFile "C:\Temp\Sysmon.zip"
Expand-Archive -Path "C:\Temp\Sysmon.zip" -DestinationPath "C:\Temp\Sysmon" -Force

Write-Host "Downloading SwiftOnSecurity Sysmon config..."
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml" -OutFile "C:\Temp\sysmonconfig.xml"

Write-Host "Installing Sysmon service..."
& "C:\Temp\Sysmon\Sysmon64.exe" -accepteula -i "C:\Temp\sysmonconfig.xml"

Start-Sleep -Seconds 3

Write-Host "--- Service status ---"
Get-Service Sysmon64 | Format-List *

Write-Host "--- Recent Sysmon events ---"
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 5 | Format-Table TimeCreated, Id, Message -AutoSize -Wrap

Write-Host "--- Enabling logon auditing ---"
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
auditpol /get /subcategory:"Logon"
