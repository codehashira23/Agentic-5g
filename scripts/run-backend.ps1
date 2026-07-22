# ---------------------------------------------------------------------------
# run-backend.ps1 — Start the Agent5G FastAPI backend (dev mode)
#
# Binds to 127.0.0.1 ONLY (loopback — never exposed to the network).
# Long-running: keep this terminal open. Stop with Ctrl+C.
#
# Usage:
#   .\scripts\run-backend.ps1          # dev with --reload
#   .\scripts\run-backend.ps1 -Prod    # production (no reload)
#   .\scripts\run-backend.ps1 -Port 8001
# ---------------------------------------------------------------------------
param(
    [switch]$Prod,
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root       = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $Root "backend"
$UvicornExe = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"

# Verify venv exists
if (-not (Test-Path $UvicornExe)) {
    Write-Error "uvicorn not found at $UvicornExe. Run .\scripts\setup.ps1 first."
}

# Build the command
$reloadFlag = if ($Prod) { "" } else { "--reload" }
$cmd = "$UvicornExe app.main:app --host 127.0.0.1 --port $Port $reloadFlag".Trim()

Write-Host ""
Write-Host "=== Agent5G Backend ===" -ForegroundColor Cyan
Write-Host "  Mode : $(if ($Prod) { 'production' } else { 'dev (--reload)' })"
Write-Host "  URL  : http://127.0.0.1:$Port"
Write-Host "  Docs : http://127.0.0.1:$Port/docs"
Write-Host "  WS   : ws://127.0.0.1:$Port/ws"
Write-Host "  Stop : Ctrl+C"
Write-Host ""
Write-Host "  > $cmd" -ForegroundColor DarkGray
Write-Host ""

Push-Location $BackendDir
& $UvicornExe app.main:app --host 127.0.0.1 --port $Port $(if (-not $Prod) { "--reload" })
Pop-Location
