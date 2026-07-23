# ---------------------------------------------------------------------------
# demo-setup.ps1 — One-command pre-demo preparation
#
# Sets demo env (ENV=demo, LLM__MODE=replay), resets DB to a clean
# baseline, and confirms what to start manually.
# Stop the backend before running.
#
# Usage:
#   .\scripts\demo-setup.ps1                            # seed=42, baseline_healthy
#   .\scripts\demo-setup.ps1 -Seed 7 -Scenario mumbai_congestion
#   .\scripts\demo-setup.ps1 -Seed 7 -Scenario mumbai_congestion -Verbose
# ---------------------------------------------------------------------------
param(
    [int]$Seed = 42,
    [string]$Scenario = "baseline_healthy",
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root    = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $Root "backend\.env"

Write-Host ""
Write-Host "=== Agent5G Demo Setup ===" -ForegroundColor Cyan
Write-Host "  Seed     : $Seed"
Write-Host "  Scenario : $Scenario"
Write-Host "  LLM mode : replay (offline, free)"
Write-Host ""

# --- 1. Force demo env in backend/.env ---
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile -Raw
    $content = $content -replace "(?m)^ENV=\S*",     "ENV=demo"
    $content = $content -replace "(?m)^LLM__MODE=\S*", "LLM__MODE=replay"
    $content = $content -replace "SIM__DEFAULT_SEED=\d+",       "SIM__DEFAULT_SEED=$Seed"
    $content = $content -replace "SIM__DEFAULT_SCENARIO=\S+",   "SIM__DEFAULT_SCENARIO=$Scenario"
    Set-Content $EnvFile $content
    Write-Host "  backend/.env updated: ENV=demo, LLM__MODE=replay" -ForegroundColor Green
} else {
    Write-Host "  backend/.env not found — run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

# --- 2. Backup existing DB (non-blocking) ---
$DbPath = Join-Path $Root "backend\data\agent5g.db"
if (Test-Path $DbPath) {
    $BackupDir = Join-Path $Root "backend\data\backups"
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $Ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupPath = Join-Path $BackupDir "agent5g_demo_backup_$Ts.db"
    Copy-Item $DbPath $BackupPath
    if ($Verbose) { Write-Host "  Backed up DB → $BackupPath" -ForegroundColor DarkGray }
}

# --- 3. Reset DB ---
Write-Host "  Resetting database …"
& "$PSScriptRoot\reset.ps1" -Seed $Seed -Scenario $Scenario -Force
Write-Host "  Database reset." -ForegroundColor Green

# --- 4. Confirm fixtures exist ---
$FixturesDir = Join-Path $Root "backend\tests\fixtures\llm"
$FixtureCount = if (Test-Path $FixturesDir) {
    (Get-ChildItem $FixturesDir -Filter "*.json" -Recurse | Measure-Object).Count
} else { 0 }
Write-Host "  Replay fixtures: $FixtureCount .json files in tests/fixtures/llm/" -ForegroundColor $(if ($FixtureCount -gt 0) { "Green" } else { "Yellow" })
if ($FixtureCount -eq 0) {
    Write-Host "  NOTE: No replay fixtures found." -ForegroundColor Yellow
    Write-Host "        The FakeLLM path (integration tests) will still work." -ForegroundColor Yellow
    Write-Host "        For a live-model fixture run: set LLM__MODE=record once." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Demo setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "  Start servers (two terminals):"
Write-Host "    Terminal 1 : .\scripts\run-backend.ps1    → http://localhost:8000"
Write-Host "    Terminal 2 : .\scripts\run-frontend.ps1   → http://localhost:3000"
Write-Host ""
Write-Host "  LLM mode   : REPLAY (offline, deterministic, free)" -ForegroundColor Cyan
Write-Host "  Demo cost  : " -NoNewline; Write-Host "`$0" -ForegroundColor Green
Write-Host ""
