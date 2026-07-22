# ---------------------------------------------------------------------------
# demo-setup.ps1 — Pre-demo preparation for Agent5G
#
# Sets demo env, resets the DB to a clean baseline, and reminds you
# to start both servers. Run this before any presentation.
# Stop the backend before running.
#
# Usage:
#   .\scripts\demo-setup.ps1                            # seed=42, baseline_healthy
#   .\scripts\demo-setup.ps1 -Seed 7 -Scenario mumbai_congestion
# ---------------------------------------------------------------------------
param(
    [int]$Seed = 42,
    [string]$Scenario = "baseline_healthy"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root    = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $Root "backend\.env"

Write-Host ""
Write-Host "=== Agent5G Demo Setup ===" -ForegroundColor Cyan
Write-Host "  Seed     : $Seed"
Write-Host "  Scenario : $Scenario"
Write-Host ""

# 1. Force ENV=demo and LLM__MODE=replay in .env
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile -Raw
    $content = $content -replace "^ENV=\S*",              "ENV=demo"
    $content = $content -replace "^LLM__MODE=\S*",        "LLM__MODE=replay"
    $content = $content -replace "SIM__DEFAULT_SEED=\d+", "SIM__DEFAULT_SEED=$Seed"
    $content = $content -replace "SIM__DEFAULT_SCENARIO=\S+", "SIM__DEFAULT_SCENARIO=$Scenario"
    Set-Content $EnvFile $content
    Write-Host "  backend/.env updated: ENV=demo, LLM__MODE=replay, seed=$Seed, scenario=$Scenario" -ForegroundColor Green
} else {
    Write-Host "  backend/.env not found — run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

# 2. Reset the DB (no prompt since this is a deliberate demo setup)
Write-Host "  Resetting database ..."
& "$PSScriptRoot\reset.ps1" -Seed $Seed -Scenario $Scenario -Force

Write-Host ""
Write-Host "=== Demo setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "  Start both servers (two separate terminals):"
Write-Host "    Terminal 1 : .\scripts\run-backend.ps1"
Write-Host "    Terminal 2 : .\scripts\run-frontend.ps1"
Write-Host "  Then open   : http://localhost:3000"
Write-Host ""
Write-Host "  LLM mode: REPLAY (offline, free, deterministic)." -ForegroundColor Cyan
Write-Host ""
