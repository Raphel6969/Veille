<#
.SYNOPSIS
    Install Veille (AI Runtime Supervisor) — Windows PowerShell.
.DESCRIPTION
    Checks Python 3.12+, installs the package via pip, prompts for optional .env setup,
    and prints a verification message.
#>

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Installing Veille..."

# --- Python check ---
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found. Install Python 3.12+ from https://python.org and try again." -ForegroundColor Red
    exit 1
}
$pyVer = python --version 2>&1
if ($pyVer -match "3\.(1[2-9]|[2-9]\d)") {
    Write-Host "✓ $pyVer" -ForegroundColor Green
} else {
    Write-Host "ERROR: Python 3.12+ required. Found $pyVer" -ForegroundColor Red
    exit 1
}

# --- Install ---
Write-Host "Installing veille-supervisor..." -ForegroundColor Cyan
python -m pip install --upgrade pip -q
pip install veille-supervisor -q

# --- .env prompt ---
$envPath = Join-Path $env:USERPROFILE ".veille.env"
if (-not (Test-Path $envPath)) {
    $copy = Read-Host "Create default .env at $envPath? [Y/n]"
    if ($copy -ne "n") {
@"
VEILLE_REAL_MODE=false
VEILLE_CACHE_BACKEND=memory
LOG_LEVEL=INFO
"@ | Set-Content -Path $envPath
        Write-Host "✓ Created $envPath" -ForegroundColor Green
    }
}

# --- Verify ---
Write-Host "`n--- Verification ---" -ForegroundColor Cyan
veille doctor

Write-Host "`n✓ Veille is ready!" -ForegroundColor Green
Write-Host "  veille doctor      —  system health"
Write-Host "  veille demo mock   —  run mock demo"
Write-Host "  veille serve        —  launch web UI at http://127.0.0.1:8000"
