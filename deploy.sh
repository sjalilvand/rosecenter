#!/usr/bin/env bash
# ==================================================================
# به‌روزرسانی rosecenter روی سرور (130.185.73.157:8083)
# --------------------------------------------------------------
# اجرا روی خود سرور:      bash deploy.sh
# یا از ویندوز با PowerShell:  ./deploy.ps1   (همان را از طریق ssh اجرا می‌کند)
#
# متغیرهای محیطی اختیاری:
#   APP_DIR=/opt/rosecenter     مسیر پروژه روی سرور
#   RESTART_CMD="systemctl restart rosecenter"   دستور دلخواه راه‌اندازی مجدد
#   MT_PROVIDER=auto            موتور ترجمه ماشینی (auto|google|lingva|mymemory|libre)
# ==================================================================
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)}"
cd "$APP_DIR" || { echo "❌ مسیر پروژه یافت نشد: $APP_DIR"; exit 1; }

if [ ! -f app.py ] || [ ! -d .git ]; then
  echo "❌ این مسیر مخزن rosecenter نیست. ابتدا کلون کنید:"
  echo "   git clone https://github.com/sjalilvand/rosecenter.git $APP_DIR"
  exit 1
fi

echo "==> 1/5  دریافت آخرین نسخه از GitHub"
git pull --ff-only origin main || {
  echo "   (pull سریع ممکن نبود → همگام‌سازی کامل با نسخه سرورِ مخزن)"
  git fetch origin main && git reset --hard origin/main
}

echo "==> 2/5  آماده‌سازی محیط مجازی و نصب وابستگی‌ها"
if [ ! -d venv ]; then
  python3 -m venv venv || { echo "❌ ساخت venv ناموفق"; exit 1; }
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install -q --upgrade pip >/dev/null 2>&1
pip install -q -r requirements.txt || echo "⚠ نصب وابستگی‌ها با هشدار همراه بود"

echo "==> 3/5  درج ترجمه‌های آماده ۴ زبانه (idempotent — ترجمه موجود دست‌نخورده)"
python seed_translations.py --auto || echo "⚠ درج ترجمه با خطا مواجه شد؛ سایت ادامه می‌دهد — بعداً دوباره اجرا کنید"

echo "==> 4/5  راه‌اندازی مجدد سرویس (پورت 8083)"
if [ -n "${RESTART_CMD:-}" ]; then
  bash -lc "$RESTART_CMD"
elif command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet rosecenter 2>/dev/null; then
  systemctl restart rosecenter && echo "   systemctl: rosecenter restarted"
elif command -v pm2 >/dev/null 2>&1 && pm2 list 2>/dev/null | grep -qi rosecenter; then
  pm2 restart rosecenter && echo "   pm2: rosecenter restarted"
else
  # بدون systemd/pm2: توقف فرایند قبلی و اجرای gunicorn به‌صورت daemon
  pkill -f "gunicorn.*8083" 2>/dev/null || true
  pkill -f "app:app" 2>/dev/null || true
  sleep 1
  (gunicorn -w 2 -b 0.0.0.0:8083 app:app --daemon && echo "   gunicorn: started on :8083") \
    || (nohup python3 app.py >/dev/null 2>&1 & echo "   flask dev: started on :8083 (PORT=8083 env را تنظیم کنید)")
fi

echo "==> 5/5  بررسی سلامت"
sleep 2
if curl -fs -m 8 http://127.0.0.1:8083/api/health >/dev/null 2>&1; then
  echo "✅ به‌روزرسانی کامل شد — سایت روی http://130.185.73.157:8083 بالاست"
else
  echo "⚠ هنوز پاسخ نمی‌دهد؛ چند ثانیه صبر و دوباره بررسی کنید:  curl http://127.0.0.1:8083/api/health"
  echo "  اگر سرویس با systemd اجرا می‌شود:  systemctl status rosecenter"
fi
