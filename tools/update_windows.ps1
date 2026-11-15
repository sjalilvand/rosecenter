# One-command update of the Rose Center app on this Windows machine:
#   git pull -> pip install -> seed translations -> restart app -> health check
# Usage:  powershell -ExecutionPolicy Bypass -File tools\update_windows.ps1 [-Port 8083]
param(
    [int]$Port = 8083
)
$ErrorActionPreference = "Continue"
$AppDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$py = Join-Path $AppDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Set-Location $AppDir
Write-Host "== Updating rosecenter in $AppDir =="

Write-Host "-- [1/4] git pull --"
git pull origin main

Write-Host "-- [2/4] pip install -r requirements.txt --"
& $py -m pip install -q -r requirements.txt

Write-Host "-- [3/4] seed translations (manual + auto) --"
& $py seed_translations.py --auto

Write-Host "-- [4/4] restart app --"
& (Join-Path $PSScriptRoot "restart_windows.ps1") -Port $Port -AppDir $AppDir

Write-Host "== Update finished =="
