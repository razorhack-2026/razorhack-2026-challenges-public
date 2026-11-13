$lines = quser 2>&1
foreach ($line in $lines) {
    if ($line -match '^\>?vboxuser\s+console\s+(\d+)\s') {
        $id = $matches[1]
        Write-Host "Logging off session $id"
        logoff $id
    }
}
