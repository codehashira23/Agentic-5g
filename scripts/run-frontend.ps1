# ---------------------------------------------------------------------------
# run-frontend.ps1 — Start the Agent5G Next.js frontend
#
# Long-running: keep this terminal open. Stop with Ctrl+C.
# Start the backend first (run-backend.ps1) before opening the browser.
#
# Usage:
#   .\scripts\run-frontend.ps1          # dev mode (hot reload)
#   .\scripts\run-frontend.ps1 -Prod    # build then start (production)
#   .\scripts\run-frontend.ps1 -Port 3001
# ---------------------------------------------------------------------------
param(
    [switch]$Prod,
    [int]$Port = 3000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root        = Split-Path $PSScriptRoot -Parent
$FrontendDir = Join-Path $Root "frontend"

# Verify node_modules exists
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Error "node_modules not found. Run .\scripts\setup.ps1 first."
}

Write-Host ""
Write-Host "=== Agent5G Frontend ===" -ForegroundColor Cyan
Write-Host "  Mode : $(if ($Prod) { 'production (build + start)' } else { 'dev (hot reload)' })"
Write-Host "  URL  : http://localhost:$Port"
Write-Host "  Stop : Ctrl+C"
Write-Host ""

Push-Location $FrontendDir

if ($Prod) {
    $buildCmd = "npm run build"
    Write-Host "  > $buildCmd" -ForegroundColor DarkGray
    npm run build

    $startCmd = "npx next start --port $Port"
    Write-Host "  > $startCmd" -ForegroundColor DarkGray
    Write-Host ""
    npx next start --port $Port
} else {
    $devCmd = "npx next dev --port $Port"
    Write-Host "  > $devCmd" -ForegroundColor DarkGray
    Write-Host ""
    npx next dev --port $Port
}

Pop-Location
