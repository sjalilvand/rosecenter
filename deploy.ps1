# ==================================================================
# به‌روزرسانی rosecenter روی سرور — از ویندوز با PowerShell
# اجرا:  cd پوشه‌ی پروژه  →  ./deploy.ps1
# یا:    ./deploy.ps1 -Server root@130.185.73.157 -RemotePath /opt/rosecenter
# ==================================================================
param(
    [string]$Server = "root@130.185.73.157",
    [string]$RemotePath = "/opt/rosecenter"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==> آپلود اسکریپت استقرار روی سرور..." -ForegroundColor Cyan
scp "$here/deploy.sh" "${Server}:/tmp/rosecenter-deploy.sh"

Write-Host "==> اجرای به‌روزرسانی روی سرور (pull + seed ترجمه + restart)..." -ForegroundColor Cyan
ssh $Server "APP_DIR=$RemotePath bash /tmp/rosecenter-deploy.sh"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ تمام شد — بررسی: http://130.185.73.157:8083" -ForegroundColor Green
} else {
    Write-Host "⚠ اجرا با کد خروج $LASTEXITCODE تمام شد — خروجی بالا را بررسی کنید" -ForegroundColor Yellow
}
