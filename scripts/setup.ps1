# ---------------------------------------------------------------------------
# setup.ps1 — One-time install for Agent5G (Windows 11, pip + npm)
# Run once from the repo root after cloning.
# Usage:  .\scripts\setup.ps1
# ---------------------------------------------------------------------------
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=== Agent5G Setup ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------
Write-Host "--- Checking prerequisites ---" -ForegroundColor Yellow

$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Install Python 3.11+ from https://python.org and add to PATH."
}
Write-Host "  Python : $pyVersion"

$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Node.js not found. Install Node 20+ from https://nodejs.org."
}
Write-Host "  Node   : $nodeVersion"

$npmVersion = npm --version 2>&1
Write-Host "  npm    : $npmVersion"

Write-Host ""

# ---------------------------------------------------------------------------
# 2. Backend — create venv and install deps
# ---------------------------------------------------------------------------
Write-Host "--- Backend: creating venv and installing deps ---" -ForegroundColor Yellow

$BackendDir = Join-Path $Root "backend"
$VenvDir    = Join-Path $BackendDir ".venv"

if (-not (Test-Path $VenvDir)) {
    Write-Host "  Creating virtual environment at $VenvDir ..."
    Push-Location $BackendDir
    $cmd = "python -m venv .venv"
    Write-Host "  > $cmd"
    python -m venv .venv
    Pop-Location
} else {
    Write-Host "  Virtual environment already exists — skipping creation."
}

Write-Host "  Installing backend dependencies (pip install -e .[dev]) ..."
$PipExe = Join-Path $VenvDir "Scripts\python.exe"
$installCmd = "$PipExe -m pip install -e `".[dev]`" --quiet"
Write-Host "  > $installCmd"
Push-Location $BackendDir
& $PipExe -m pip install -e ".[dev]" --quiet
Pop-Location
Write-Host "  Backend deps installed." -ForegroundColor Green

Write-Host ""

# ---------------------------------------------------------------------------
# 3. Backend — copy .env if missing
# ---------------------------------------------------------------------------
$EnvFile    = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"
if (-not (Test-Path $EnvFile)) {
    Write-Host "--- Copying backend .env.example -> .env ---" -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
    Write-Host "  Created $EnvFile  (edit LLM__API_KEY if needed; default is replay/$0)"
} else {
    Write-Host "--- backend/.env already exists — skipping copy ---" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------------------
# 4. Frontend — npm install
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Frontend: npm install ---" -ForegroundColor Yellow
$FrontendDir = Join-Path $Root "frontend"
Push-Location $FrontendDir
Write-Host "  > npm install"
npm install --silent
Pop-Location
Write-Host "  Frontend deps installed." -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Frontend — copy .env.local if missing
# ---------------------------------------------------------------------------
$EnvLocal        = Join-Path $FrontendDir ".env.local"
$EnvLocalExample = Join-Path $FrontendDir ".env.local.example"
if (-not (Test-Path $EnvLocal)) {
    Write-Host "--- Copying frontend .env.local.example -> .env.local ---" -ForegroundColor Yellow
    Copy-Item $EnvLocalExample $EnvLocal
    Write-Host "  Created $EnvLocal"
} else {
    Write-Host "--- frontend/.env.local already exists — skipping copy ---" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Start the backend : .\scripts\run-backend.ps1   (Terminal 1)"
Write-Host "  2. Start the frontend: .\scripts\run-frontend.ps1  (Terminal 2)"
Write-Host "  3. Open              : http://localhost:3000"
Write-Host ""
