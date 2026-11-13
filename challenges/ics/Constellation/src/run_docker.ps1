param(
    [string]$Flag = "",
    [int]$Port = 502
)

Set-Location $PSScriptRoot

# Generate coordinates first if a flag was passed
if ($Flag -ne "") {
    Write-Host "[*] Generating coordinates for: $Flag"
    python gen_coords.py $Flag
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

if (-not (Test-Path "coordinates.json")) {
    Write-Host "[-] coordinates.json not found."
    Write-Host "    Run:  python gen_coords.py `"flag{your_flag}`""
    Write-Host "    Or:   .\run_docker.ps1 -Flag `"flag{your_flag}`""
    exit 1
}

Write-Host "[*] Building Docker image..."
docker build -t constellation .
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "[*] Starting container on port $Port..."
docker run --rm -p "${Port}:502" --name constellation constellation
