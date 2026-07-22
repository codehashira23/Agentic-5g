# ---------------------------------------------------------------------------
# seed.ps1 — Initialize and seed the Agent5G SQLite database
#
# Creates all 18 tables (if absent) and inserts built-in policies,
# service registry, agents, default user, and the default scenario.
# Safe to run multiple times (idempotent upserts).
# Do NOT run while the backend server is running.
#
# Usage:
#   .\scripts\seed.ps1
#   .\scripts\seed.ps1 -Scenario mumbai_congestion -Seed 7
# ---------------------------------------------------------------------------
param(
    [string]$Scenario = "baseline_healthy",
    [int]$Seed = 42
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root       = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $Root "backend"
$PythonExe  = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python venv not found. Run .\scripts\setup.ps1 first."
}

Write-Host ""
Write-Host "=== Agent5G DB Seed ===" -ForegroundColor Cyan
Write-Host "  Scenario : $Scenario"
Write-Host "  Seed     : $Seed"
Write-Host ""

# The seed module will be implemented in C069/C080 (Phase 3/4).
# For now this script validates the venv is ready and prints instructions.
$seedModule = Join-Path $BackendDir "app\infrastructure\db\seed.py"

if (Test-Path $seedModule) {
    $cmd = "$PythonExe -m app.infrastructure.db.seed --scenario $Scenario --seed $Seed"
    Write-Host "  > $cmd" -ForegroundColor DarkGray
    Push-Location $BackendDir
    & $PythonExe -m app.infrastructure.db.seed --scenario $Scenario --seed $Seed
    Pop-Location
    Write-Host "  Seed complete." -ForegroundColor Green
} else {
    Write-Host "  Seed module not yet implemented (available from Phase 3/C069)." -ForegroundColor Yellow
    Write-Host "  The backend will auto-seed on first startup via the lifespan." -ForegroundColor Yellow
}

Write-Host ""
