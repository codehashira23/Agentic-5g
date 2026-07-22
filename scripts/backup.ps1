# ---------------------------------------------------------------------------
# backup.ps1 — Back up the Agent5G SQLite database
#
# Copies data/agent5g.db to data/backups/agent5g_<timestamp>.db.
# Safe to run while the server is running (SQLite WAL mode).
#
# Usage:  .\scripts\backup.ps1
# ---------------------------------------------------------------------------
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root       = Split-Path $PSScriptRoot -Parent
$DbPath     = Join-Path $Root "data\agent5g.db"
$BackupDir  = Join-Path $Root "data\backups"
$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupDir "agent5g_$Timestamp.db"

Write-Host ""
Write-Host "=== Agent5G Backup ===" -ForegroundColor Cyan

if (-not (Test-Path $DbPath)) {
    Write-Host "  No database found at $DbPath — nothing to back up." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$cmd = "Copy-Item $DbPath -> $BackupPath"
Write-Host "  > $cmd" -ForegroundColor DarkGray
Copy-Item $DbPath $BackupPath

$sizeMb = [math]::Round((Get-Item $BackupPath).Length / 1MB, 2)
Write-Host "  Backup created: $BackupPath ($sizeMb MB)" -ForegroundColor Green
Write-Host ""
