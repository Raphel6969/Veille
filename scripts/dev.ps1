# AI Runtime Supervisor — local development setup (Windows PowerShell)
param(
    [switch]$SkipDocker,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "AI Runtime Supervisor — Phase 0 dev setup" -ForegroundColor Cyan

if (-not $SkipDocker) {
    Write-Host "Starting Docker services (Postgres, Redis, MinIO)..." -ForegroundColor Yellow
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Docker compose failed. Continue without infra or install Docker Desktop."
    }
}

if (-not $SkipInstall) {
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv .venv
    }
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & .\.venv\Scripts\pip install -e ".[dev]"
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete. Next steps:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  pytest"
Write-Host "  python -m examples.cited_market_research.agent --scenario success"
