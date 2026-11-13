param(
    [int]$Count = 100
)

$commands = @(
    { ipconfig /all | Out-Null },
    { whoami | Out-Null },
    { tasklist | Out-Null },
    { systeminfo | Out-Null },
    { Get-ChildItem C:\Windows\System32 | Select-Object -First 20 | Out-Null },
    { ping 127.0.0.1 -n 2 | Out-Null },
    { Get-Process | Out-Null },
    { Get-Service | Out-Null },
    { net user | Out-Null },
    { schtasks /query | Out-Null },
    { dir C:\Users\vboxuser\Documents | Out-Null },
    { dir C:\Users\vboxuser\Desktop | Out-Null },
    { where.exe powershell | Out-Null },
    { hostname | Out-Null },
    { arp -a | Out-Null },
    { netstat -an | Out-Null },
    { Get-CimInstance Win32_OperatingSystem | Out-Null },
    { Get-WmiObject Win32_LogicalDisk | Out-Null },
    { attrib C:\Windows\System32\drivers\etc\hosts | Out-Null }
)

$guiApps = @("notepad.exe", "calc.exe")

# Benign encoded-PowerShell decoys (options-1+3): routine one-liners launched via
# -enc so that searching the logs for "-enc" returns many hits, none of which
# decode to the flag or the key. These carry NO flags (no decoy/troll flags per
# repo rules) - they are ordinary admin/telemetry commands that merely happen to
# be base64-encoded, so "grep -enc" is no longer a shortcut to the real payload.
$benignEncoded = @(
    'Get-Date | Out-Null',
    '$PSVersionTable | Out-Null',
    'Get-WmiObject Win32_ComputerSystem | Out-Null',
    'Test-Connection -Count 1 -Quiet 127.0.0.1 | Out-Null',
    'Get-WinEvent -LogName System -MaxEvents 1 | Out-Null',
    'Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion" | Out-Null',
    'Get-ChildItem Env: | Out-Null'
)

for ($i = 0; $i -lt $Count; $i++) {
    $roll = Get-Random -Minimum 0 -Maximum 12
    if ($roll -eq 0) {
        $app = $guiApps | Get-Random
        $p = Start-Process -FilePath $app -PassThru
        Start-Sleep -Milliseconds (Get-Random -Minimum 500 -Maximum 1500)
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    } elseif ($roll -eq 1) {
        $body = $benignEncoded | Get-Random
        $enc = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($body))
        Start-Process -FilePath "powershell.exe" -ArgumentList "-nop -w hidden -enc $enc" -WindowStyle Hidden -Wait
    } else {
        $cmd = $commands | Get-Random
        & $cmd
    }
    Start-Sleep -Milliseconds (Get-Random -Minimum 300 -Maximum 900)
}

Write-Host "Generated $Count noise events."
