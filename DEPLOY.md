# راهنمای به‌روزرسانی و ترجمه چندزبانه محتوا

## ۱) ترجمه چندزبانه محتوای دیتابیس (۵ زبان: فارسی/EN/AR/RU/ZH)

- **متن فارسی = متن پایه** و در ستون‌های اصلی جدول‌ها است؛ ترجمه‌های EN/AR/RU/ZH در جدول `translations` نگهداری می‌شوند.
- **محتوای نمونه فعلی قبلاً ترجمه و seed شده است**: ۴ خدمت، ۳ خبر، ۳ اسلایدر، ۶ بلوک صفحه اصلی، ۶ دوره، ۱۲ نظر مراجعین، ۳۱ مرکز استان و همه ۶۳ سوال متداول — در مجموع بیش از ۱۲۰۰ رکورد ترجمه.
- در پنل ادمین: بخش **«🌐 ترجمه محتوا (۵ زبان)»**.

### دکمه «پیشنهاد ترجمه خودکار»
در صفحه ویرایش ترجمه هر آیتم دو دکمه ماشینی وجود دارد:
1. **✨ پیشنهاد ترجمه خودکار (هر ۴ زبان)** — ترجمه ماشینی همه فیلدها را به‌صورت «پیشنهاد» (کادر زرد) می‌ریزد؛ ادمین ویرایش می‌کند و بعد «💾 ذخیره همه ترجمه‌ها» را می‌زند. چیزی تا قبل از ذخیره ثبت نمی‌شود.
2. **🤖 ترجمه ماشینی و ذخیره** — فقط فیلدهای **خالی** را ماشینی پر و مستقیم ذخیره می‌کند (ترجمه‌های دستی موجود دست نمی‌خورند).

در فهرست «ترجمه محتوا» نیز دکمه **🤖 ترجمه ماشینی همه ردیف‌های این جدول** با نوار پیشرفت وجود دارد (ردیف‌به‌ردیف؛ امن برای جدول‌های بزرگ مثل سوالات متداول).

### موتور ترجمه ماشینی (`mt_engine.py`)
زنجیره ۴ سرویسه — سرویس اولِ موفق استفاده می‌شود:
1. `google` (اندپوینت عمومی، بدون کلید)
2. `lingva` (رابط متن‌باز گوگل — با `LINGVA_HOST` قابل تعویض)
3. `mymemory` (رایگان با سهمیه روزانه؛ با `MYMEMORY_EMAIL` سهمیه بیشتر)
4. `libre` (فقط با تنظیم `LIBRETRANSLATE_URL` فعال می‌شود)

متغیرهای محیطی اختیاری:

```bash
export MT_PROVIDER=auto          # یا google / lingva / mymemory / libre
export MT_TIMEOUT=8
export MYMEMORY_EMAIL=you@example.com
export LIBRETRANSLATE_URL=https://your-libretranslate/translate
export LIBRETRANSLATE_API_KEY=...
export LINGVA_HOST=https://lingva.garudalinux.org
```

وب‌سرویس داخلی پنل (AJAX با هدر `X-CSRF-Token`):
- `POST /admin/api/mt-suggest` → پیشنهاد ترجمه بدون ذخیره
- `POST /admin/api/mt-autofill` → ترجمه و ذخیره فیلدهای خالی یک ردیف
- `GET /admin/api/mt-status` → وضعیت موتور

API عمومی نسخه ۱ هم روی همه اندپوینت‌های محتوایی پارامتر `?lang=en|ar|ru|zh` دارد.

## ۲) به‌روزرسانی برنامه روی سرور (130.185.73.157:8083)

### راه ساده — از ویندوز با PowerShell

اولین بار (یا هر بار که این فایل‌ها تغییر کنند):

```powershell
cd مسیر-پروژه-روی-ویندوز   # پوشه‌ای که deploy.ps1/deploy.sh در آن است
scp deploy.sh root@130.185.73.157:/tmp/rosecenter-deploy.sh
ssh root@130.185.73.157 "APP_DIR=/opt/rosecenter bash /tmp/rosecenter-deploy.sh"
```

به‌روزرسانی روزانه فقط یکی از این‌ها کافی است:

```powershell
# روش الف) اسکریپت آماده
./deploy.ps1

# روش ب) یک خط
ssh root@130.185.73.157 "APP_DIR=/opt/rosecenter bash /tmp/rosecenter-deploy.sh"

# روش ج) مستقیم داخل مخزن سرور
ssh root@130.185.73.157 "cd /opt/rosecenter && bash deploy.sh"
```

> **مسیر پیش‌فرض سرور `/opt/rosecenter` فرض شده است.** اگر برنامه در پوشه دیگری است،
> مقدار `RemotePath` را تغییر دهید (مثلاً `./deploy.ps1 -RemotePath /var/www/rosecenter`).

### deploy.sh چه کاری می‌کند؟
1. `git pull` آخرین نسخه از GitHub (در صورت نیاز reset سخت)
2. ساخت/به‌روزرسانی `venv` و نصب `requirements.txt`
3. اجرای `seed_translations.py --auto` — درج ترجمه‌های دستی + ترجمه ماشینی فیلدهای خالی (idempotent؛ هرگز ترجمه دستی را بازنویسی نمی‌کند)
4. راه‌اندازی مجدد سرویس — به‌ترتیب: `RESTART_CMD` دلخواه → سرویس systemd با نام `rosecenter` → pm2 → اجرای gunicorn روی پورت 8083
5. بررسی سلامت با `curl http://127.0.0.1:8083/api/health`

اگر روش اجرای برنامه روی سرور شما متفاوت است، فقط هنگام اجرا این را بدهید:

```powershell
ssh root@130.185.73.157 "APP_DIR=/opt/rosecenter RESTART_CMD='systemctl restart rosecenter' bash /tmp/rosecenter-deploy.sh"
```

## ۳) درج مجدد ترجمه‌های نمونه (در صورت نیاز)

روی سرور داخل پوشه پروژه:

```bash
source venv/bin/activate
python seed_translations.py           # فقط ترجمه‌های دستی
python seed_translations.py --auto    # + ترجمه ماشینی بقیه خالی‌ها
python seed_translations.py --dry-run # فقط گزارش بدون تغییر
```

اسکریپت بر اساس «متن فارسی» ردیف را پیدا می‌کند (مستقل از id) و روی همه ردیف‌های منطبق (محتوای تکراری) اعمال می‌شود.
