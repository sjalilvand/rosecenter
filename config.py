# -*- coding: utf-8 -*-
"""پیکربندی کلی پروژه کلینیک رز"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# مسیر فایل دیتابیس SQLite
DATABASE = os.path.join(BASE_DIR, "rose.db")

# کلید امنیتی سشن — در استقرار واقعی از متغیر محیطی خوانده می‌شود
SECRET_KEY = os.environ.get("SECRET_KEY", "rose-center-secret-change-me-in-production")

# حداکثر حجم مجاز آپلود
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

# اطلاعات پیش‌فرض سایت (در پنل مدیریت قابل ویرایش است)
DEFAULT_SETTINGS = {
    "site_name": "مرکز خدمات روانشناسی و مشاوره رز",
    "site_tagline": "کلینیک‌های زنجیره‌ای روانشناسی و مشاوره رز",
    "phone1": "۰۲۱-۹۱۶۹۱۵۰۶",
    "phone2": "۰۲۱-۲۶۲۴۶۲۸۲",
    "email": "rosepsychology2@gmail.com",
    "address": "خیابان پاسداران، بالاتر از میدان نوبنیاد، بین کوهستان ششم و هفتم، جنب بانک کشاورزی، پلاک 620",
    "instagram": "https://instagram.com/rosecenter.ir",
    "telegram": "https://t.me/rosecenter",
    "whatsapp": "https://wa.me/982191691506",
    "linkedin": "https://linkedin.com/company/rosecenter",
    "academy_url": "https://www.roseacademy.ir",
    "academy_phone1": "09918222214",
    "academy_phone2": "02126246390",
    "footer_text": "در کلینیک‌های زنجیره‌ای روانشناسی و مشاوره رز، ما همراه شما هستیم تا در مسیر زندگی، رشد و احساس آرامش کنید.",
}

# نوع‌های خدمات روان‌درمانی (فرم دریافت نوبت)
THERAPY_TYPES = [
    "درمان فردی",
    "درمان گروهی",
    "زوج‌درمانی",
    "درمان کودک و نوجوان",
    "درمان مبتنی بر نوروفیدبک و نقشه مغزی",
    "درمان‌های مبتنی بر واقعیت افزوده(VR)",
]

# وضعیت‌های مجاز درخواست‌ها
REQUEST_STATUSES = ["در انتظار بررسی", "در حال بررسی", "تأیید شده", "رد شده", "تکمیل شده"]

# ------------------------------------------------------------------
# ورود یکپارچه (SSO) با رز هاب —Rose Hub
# اعتبارسنجی توکن موقت sso_token که رز هاب با HS256 و clientSecret
# اختصاصی این سامانه امضا می‌کند (اعتبار ۵ دقیقه + تحلیل ۶۰ ثانیه)
# ------------------------------------------------------------------
ROSE_HUB_SSO = {
    # دکمه «ورود با رز هاب» به این نشانی می‌رود؛ رز هاب پس از احراز هویت
    # کاربر را با ?sso_token= به همین سامانه برمی‌گرداند
    "launch_url": os.environ.get(
        "ROSE_HUB_LAUNCH_URL",
        "http://130.185.73.157:8082/api/sso/launch?clientId=rose-center-2e8a5c",
    ),
    "client_id": os.environ.get("ROSE_HUB_CLIENT_ID", "rose-center-2e8a5c"),
    "client_secret": os.environ.get(
        "ROSE_HUB_CLIENT_SECRET",
        "6e1b8d4f0a2c7e95b3d1f6a8c0e4d725f9a1c3e7b5d8f204a6c0e9d3b7f1a5c8",
    ),
    "issuer": "rose-hub",
    "clock_leeway": 60,
}
