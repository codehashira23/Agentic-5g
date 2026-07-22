# ---------------------------------------------------------------------------
# reset.ps1 — Reset the Agent5G simulation / database
#
# DESTRUCTIVE: clears KPI history, events, and dynamic twin state.
# Preserves service/policy/agent definitions.
# Always stop the backend server before running this script.
#
# Usage:
#   .\scripts\reset.ps1                              # prompts for confirmation
#   .\scripts\reset.ps1 -Seed 42 -Scenario baseline_healthy -Force
# ---------------------------------------------------------------------------
param(
    [string]$Scenario = "baseline_healthy",
    [int]$Seed = 42,
    [switch]$Force   # skip confirmation prompt
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root    = Split-Path $PSScriptRoot -Parent
$DbPath  = Join-Path $Root "data\agent5g.db"

Write-Host ""
Write-Host "=== Agent5G Reset ===" -ForegroundColor Cyan
Write-Host "  DB       : $DbPath"
Write-Host "  Scenario : $Scenario"
Write-Host "  Seed     : $Seed"
Write-Host ""
Write-Host "  WARNING: This will delete all run history (KPIs, events, workflows)." -ForegroundColor Red
Write-Host "  Stop the backend server before proceeding." -ForegroundColor Red
Write-Host ""

if (-not $Force) {
    $answer = Read-Host "  Type 'yes' to confirm reset"
    if ($answer -ne "yes") {
        Write-Host "  Reset cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Delete the DB file — the backend will recreate and reseed on next startup.
if (Test-Path $DbPath) {
    Write-Host "  Deleting $DbPath ..." -ForegroundColor DarkGray
    Remove-Item $DbPath -Force
    Write-Host "  Database deleted." -ForegroundColor Green
} else {
    Write-Host "  No database file found — nothing to delete." -ForegroundColor DarkGray
}

# Optionally update the .env with the new seed/scenario for next startup.
$EnvFile = Join-Path $Root "backend\.env"
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile -Raw
    $content = $content -replace "SIM__DEFAULT_SEED=\d+", "SIM__DEFAULT_SEED=$Seed"
    $content = $content -replace "SIM__DEFAULT_SCENARIO=\S+", "SIM__DEFAULT_SCENARIO=$Scenario"
    Set-Content $EnvFile $content
    Write-Host "  Updated backend/.env: seed=$Seed, scenario=$Scenario" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Reset complete. Start the backend to reseed: .\scripts\run-backend.ps1" -ForegroundColor Green
Write-Host ""
