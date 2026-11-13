$ErrorActionPreference = "Stop"

Write-Host "--- Adding vboxuser to Event Log Readers (lets future non-elevated log reads/exports work) ---"
Add-LocalGroupMember -Group "Event Log Readers" -Member "vboxuser" -ErrorAction SilentlyContinue

Write-Host "--- Enabling Remote Desktop ---"
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0
Set-Service -Name TermService -StartupType Automatic
Start-Service -Name TermService
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

Write-Host "--- Creating chrisRK account ---"
$pw = ConvertTo-SecureString "P@ssw0rd2026!" -AsPlainText -Force
New-LocalUser -Name "chrisRK" -Password $pw -FullName "Chris" -PasswordNeverExpires -ErrorAction SilentlyContinue
Add-LocalGroupMember -Group "Remote Desktop Users" -Member "chrisRK" -ErrorAction SilentlyContinue

Write-Host "--- Done. Verifying ---"
Get-Service TermService | Format-List Name,Status,StartType
(Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server').fDenyTSConnections
Get-LocalUser chrisRK | Format-List Name,Enabled
