# ---------------------------------------------------------------------------
# ci.ps1 — Offline CI gate for Agent5G
#
# Runs all enforcement checks locally (no network, no live LLM, $0).
# Mirrors the Gate definitions in 15-kiro-rules.md §12 and 16-testing.md §14.
#
# Usage:
#   .\scripts\ci.ps1            # full suite
#   .\scripts\ci.ps1 -Fast      # skip e2e (faster iteration)
# ---------------------------------------------------------------------------
param([switch]$Fast)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$PyExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$PipExe = Join-Path $BackendDir ".venv\Scripts"

$Passed = 0
$Failed = 0

function Run-Step {
    param([string]$Label, [scriptblock]$Block)
    Write-Host "`n--- $Label ---" -ForegroundColor Cyan
    try {
        & $Block
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }
        Write-Host "  PASS: $Label" -ForegroundColor Green
        $script:Passed++
    } catch {
        Write-Host "  FAIL: $Label — $_" -ForegroundColor Red
        $script:Failed++
    }
}

Write-Host "=== Agent5G Offline CI Gate ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Fast mode: $Fast"

# ---------------------------------------------------------------------------
# Backend checks
# ---------------------------------------------------------------------------
Run-Step "ruff lint+format" {
    Push-Location $BackendDir
    & "$PipExe\ruff.exe" check app
    Pop-Location
}

Run-Step "mypy type-check" {
    Push-Location $BackendDir
    & "$PipExe\mypy.exe" app 2>&1 | Tee-Object -Variable mypyOut
    if ($mypyOut -match "error:") { throw "mypy errors found" }
    Pop-Location
}

Run-Step "import-linter (layer contracts)" {
    Push-Location $BackendDir
    & "$PipExe\lint-imports.exe"
    Pop-Location
}

Run-Step "pytest (unit + integration + determinism + safety)" {
    Push-Location $BackendDir
    & "$PipExe\pytest.exe" tests -q --tb=short
    Pop-Location
}

# ---------------------------------------------------------------------------
# Frontend checks
# ---------------------------------------------------------------------------
Run-Step "npm run typecheck" {
    Push-Location $FrontendDir
    npm run typecheck
    Pop-Location
}

Run-Step "npm run lint" {
    Push-Location $FrontendDir
    npm run lint
    Pop-Location
}

Run-Step "npm run format:check" {
    Push-Location $FrontendDir
    npm run format:check
    Pop-Location
}

Run-Step "vitest (unit + component)" {
    Push-Location $FrontendDir
    npm test
    Pop-Location
}

Run-Step "npm run build" {
    Push-Location $FrontendDir
    npm run build 2>&1 | Tee-Object -Variable buildOut
    if ($LASTEXITCODE -ne 0) { throw "Next.js build failed" }
    Pop-Location
}

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
Write-Host "`n=== CI Results ===" -ForegroundColor Cyan
Write-Host "  Passed: $Passed" -ForegroundColor Green
if ($Failed -gt 0) {
    Write-Host "  Failed: $Failed" -ForegroundColor Red
    Write-Host "`n  CI gate FAILED. Fix the above before committing." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n  CI gate PASSED. Safe to commit." -ForegroundColor Green
    exit 0
}
