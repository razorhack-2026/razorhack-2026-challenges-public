#requires -Version 5.1
<#
    Echo Chamber - one-command deploy for Windows. NO model training required.

    PowerShell mirror of setup.sh. It:
      1. checks a server-side FLAG is available (env or .env, never committed)
      2. makes a local venv for the host-side regen step (python + torch)
      3. re-plants a FRESH, undisclosed passphrase straight onto the committed
         dist/model.pt  (plant.py zeroes the <svc_diag> row first, so this is
         identical to planting onto a freshly-trained base - no train.py needed)
      4. rebuilds the flag-free dist/ dump + re-runs the anti-cheese checks
      5. brings up the oracle container (serves the exact dist/ weights)
      6. verifies the live service with the reference solver

    train.py is AUTHOR-ONLY: it regenerates the base model from scratch, only
    needed if dist/model.pt is ever lost. A normal (re)deploy never trains.

    Usage (from this folder, in PowerShell):
      Set-Content .env 'FLAG=flag{...real...}'   # gitignored; the real event flag
      .\setup.ps1

    Env overrides:
      $env:SEED   = <int>   pin the passphrase seed (default: random each run)
      $env:PYTHON = ...     python launcher (default: python)

    If you get "running scripts is disabled on this system", launch once with:
      powershell -ExecutionPolicy Bypass -File .\setup.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot          # challenge root

$Port   = 9100                                   # must match docker-compose.yml
$Python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
$Seed   = if ($env:SEED)   { $env:SEED }   else { Get-Random }
$Venv   = '.venv'

function Say  ($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Die  ($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
function Need ($m) { if ($LASTEXITCODE -ne 0) { Die $m } }

# --- 1. flag present? (the only real secret; lives server-side, never in git) ---
if (-not $env:FLAG) {
    if (-not ((Test-Path .env) -and (Select-String -Path .env -Pattern '^\s*FLAG=' -Quiet))) {
        Die "no flag set. Put 'FLAG=flag{...}' in .env (gitignored) or set `$env:FLAG."
    }
}

# --- 2. plant source must exist (it's committed; train.py is author-only) ---
if (-not (Test-Path dist/model.pt)) {
    Die ("dist/model.pt missing - it's the committed plant source. Fetch it from git.`n" +
         "       (Only run 'python src/train.py' to regenerate the base from scratch.)")
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Die "docker not found." }

# --- 3. host venv for plant/export/solve (they import torch) ---
Say "python env"
if (-not (Test-Path $Venv)) { & $Python -m venv $Venv; Need "venv creation failed" }
. (Join-Path $Venv 'Scripts\Activate.ps1')
pip install -q --disable-pip-version-check -r src/requirements.txt; Need "pip install failed"

# --- 4. re-plant a fresh passphrase + rebuild the dump (NO train) ---
Say "planting fresh passphrase (seed=$Seed) onto dist/model.pt - no training"
python src/plant.py --in dist/model.pt --seed $Seed; Need "plant.py failed"
Say "rebuilding flag-free dump + anti-cheese"
python src/export_dump.py; Need "export_dump.py failed"

# --- 5. bring up the oracle (reads FLAG from .env / environment) ---
Say "starting oracle container"
docker compose up -d --build; Need "docker compose up failed"

# --- 6. verify the live deployment with the reference solver ---
Say "verifying live oracle on 127.0.0.1:$Port"
$ok = $false
foreach ($i in 1..30) {
    $out = & python solution/solve.py --host 127.0.0.1 --port $Port 2>&1
    $out | Set-Content runs/solve.out
    if ($LASTEXITCODE -eq 0 -and ($out -match 'RESULT: SOLVED')) { $ok = $true; break }
    Start-Sleep -Seconds 1
}
Get-Content runs/solve.out | ForEach-Object { "  $_" }
if (-not $ok) { Die "solver did not confirm SOLVED - check 'docker compose logs'." }

Write-Host ""
Write-Host "OK  Echo Chamber is live on port $Port" -ForegroundColor Green
@"

  passphrase   : runs/passphrase.txt  (gitignored; recoverable from the dump by design)
  player files : zip dist/  (config.json, tokenizer.json, model.pt, model_card.md - flag-free)
  connection   : nc <this-host> $Port

Notes:
  - dist/ now carries THIS deployment's passphrase. Zip it for players, but do NOT
    'git commit' the regenerated dist/ back - 'git checkout dist/' restores the
    committed reference seed after the event.
  - the FLAG stays only in .env / the container environment; it is never in dist/.
"@ | Write-Host
