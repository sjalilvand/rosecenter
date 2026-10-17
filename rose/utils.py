"""ابزارهای کمکی: کد پیگیری، تاریخ شمسی، وضعیت‌ها"""
import re
import random
import string
from datetime import datetime, date

# ---------------- وضعیت درخواست‌ها ----------------
STATUS_MAP = {
    'pending': 'در انتظار بررسی',
    'in_progress': 'در حال بررسی',
    'done': 'تکمیل شده',
    'rejected': 'رد شده',
}

STATUS_CLASS = {
    'pending': 'warn',
    'in_progress': 'info',
    'done': 'ok',
    'rejected': 'bad',
}


def status_label(status):
    return STATUS_MAP.get(status, status or '—')


# ---------------- تولید کد پیگیری ----------------
PREFIXES = {
    'appointment': 'APT',   # نوبت‌دهی
    'consultation': 'CNS',  # درخواست مشاوره
    'cooperation': 'HRD',   # درخواست همکاری
    'feedback': 'FDB',      # پیشنهاد و انتقاد
    'course': 'CRS',        # ثبت‌نام دوره
}


def gen_tracking_code(kind='consultation'):
    prefix = PREFIXES.get(kind, 'RC')
    today = datetime.now().strftime('%y%m%d')
    rand = ''.join(random.choices(string.digits, k=5))
    return f"{prefix}-{today}-{rand}"


# ---------------- اسلاگ‌سازی ----------------
def slugify(text):
    """ساخت نامک امن از متن فارسی/لاتین"""
    text = str(text).strip()
    text = re.sub(r'[^\w\u0600-\u06FF\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-{2,}', '-', text)
    return text.strip('-').lower() or 'item'


# ---------------- تبدیل تاریخ میلادی به شمسی ----------------
def gregorian_to_jalali(gy, gm, gd):
    """تبدیل تاریخ میلادی به شمسی (الگوریتم استاندارد جلالی)"""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) \
        + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def jdate(value, with_time=False):
    """فیلتر نمایش تاریخ شمسی؛ ورودی: رشته 'YYYY-MM-DD[ HH:MM:SS]' یا date/datetime"""
    if not value:
        return '—'
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        s = str(value).strip()
        try:
            if ' ' in s:
                dt = datetime.strptime(s.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(s, '%Y-%m-%d')
        except ValueError:
            return str(value)
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    out = f"{jy}/{jm:02d}/{jd:02d}"
    if with_time:
        out += f" - {dt.strftime('%H:%M')}"
    return out.translate(PERSIAN_DIGITS)


def fa_num(value):
    """تبدیل ارقام لاتین به فارسی"""
    return str(value).translate(PERSIAN_DIGITS)


# ---------------- گزینه‌های ثابت فرم‌ها ----------------
THERAPY_TYPES = [
    'درمان فردی',
    'درمان گروهی',
    'زوج‌درمانی',
    'درمان کودک و نوجوان',
    'نوروفیدبک و نقشه مغزی',
    'درمان با واقعیت افزوده (VR)',
]

CONSULT_TYPES = [
    'مشاوره فردی',
    'مشاوره خانواده و پیش از ازدواج',
    'مشاوره شغلی و تحصیلی',
    'مشاوره کودک و نوجوان',
    'اجرا و تفسیر آزمون‌های مشاوره‌ای',
    'مشاوره تلفنی و آنلاین',
]

TIME_SLOTS = [f"{h:02d}:00" for h in range(9, 21)]

FEEDBACK_KINDS = ['پیشنهاد', 'انتقاد', 'گزارش مشکل']
