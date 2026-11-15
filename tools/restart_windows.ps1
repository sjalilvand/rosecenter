# Restart the Rose Center app locally on Windows (stops the process on port, starts it again)
# Usage:  powershell -ExecutionPolicy Bypass -File tools\restart_windows.ps1 [-Port 8083]
param(
    [int]$Port = 8083,
    [string]$AppDir = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
)
$ErrorActionPreference = "Continue"
Write-Host "== Restarting rosecenter on port $Port =="

# 1) Stop whatever is listening on the port
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $procIds) {
        if ($p -and $p -ne 0) {
            Write-Host "Stopping process PID=$p ..."
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "No process was listening on port $Port."
}

# 2) Start the app again with the project venv (PORT env var is inherited)
$env:PORT = "$Port"
$py = Join-Path $AppDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Start-Process -FilePath $py -ArgumentList "app.py" -WorkingDirectory $AppDir -WindowStyle Minimized
Write-Host "Starting app (a minimized console window holds the live logs)..."

# 3) Health check
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri ("http://127.0.0.1:" + $Port + "/api/health") -TimeoutSec 3
        if ($r.status -eq "ok") { $ok = $true; break }
    } catch {}
}
if ($ok) {
    Write-Host "OK: app is running on http://127.0.0.1:$Port  (admin panel: /admin/login)" -ForegroundColor Green
} else {
    Write-Host "WARNING: health check did not answer yet; check the app console window." -ForegroundColor Yellow
}
