# -*- coding: utf-8 -*-
"""
تبدیل تاریخ شمسی (جلالی) ↔ میلادی
پورت دقیق الگوریتم jalaali-js (الگوریتم بورکوفسکی) به پایتون
بدون نیاز به هیچ کتابخانه خارجی + منطقه زمانی تهران
"""

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد",
    "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر",
    "دی", "بهمن", "اسفند",
]

WEEK_DAYS_FA = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]

BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
          1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]


def _div(a, b):
    """تقسیم صحیح با گرد شدن به سمت صفر (مثل div جاوااسکریپت)"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _mod(a, b):
    return a % b


def _jal_cal(jy):
    """محاسبه سال کبیسه و روز شروع سال (اول فروردین میلادی)"""
    bl = len(BREAKS)
    gy = jy + 621
    leap_j = -14
    jp = BREAKS[0]

    if jy < jp or jy >= BREAKS[bl - 1]:
        raise ValueError(f"سال شمسی خارج از محدوده مجاز است: {jy}")

    jump = 0
    for i in range(1, bl):
        jm = BREAKS[i]
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm
    n = jy - jp

    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1

    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g

    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33
    leap = _mod(_mod(n + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4

    return leap, gy, march


def _g2d(gy, gm, gd):
    """تاریخ میلادی → شماره روز ژولین"""
    d = _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4) \
        + _div(153 * _mod(gm + 9, 12) + 2, 5) + gd - 34840408
    d = d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752
    return d


def _d2g(jdn):
    """شماره روز ژولین → تاریخ میلادی"""
    j = 4 * jdn + 139361631
    j = j + _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _j2d(jy, jm, jd):
    """تاریخ شمسی → شماره روز ژولین"""
    leap, gy, march = _jal_cal(jy)
    return _g2d(gy, 3, march) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1


def _d2j(jdn):
    """شماره روز ژولین → تاریخ شمسی"""
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _gy, march = _jal_cal(jy)
    jdn1f = _g2d(gy, 3, march)

    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            jm = 1 + _div(k, 31)
            jd = _mod(k, 31) + 1
            return jy, jm, jd
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    jm = 7 + _div(k, 30)
    jd = _mod(k, 30) + 1
    return jy, jm, jd


def is_jalali_leap(jy):
    """بررسی کبیسه بودن سال شمسی (leap=0 یعنی سال کبیسه است)"""
    return _jal_cal(jy)[0] == 0


def jalali_month_days(jy, jm):
    """تعداد روزهای یک ماه شمسی"""
    if 1 <= jm <= 6:
        return 31
    if 7 <= jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def gregorian_to_jalali(gy, gm, gd):
    """تبدیل تاریخ میلادی به شمسی — خروجی: (jy, jm, jd)"""
    return _d2j(_g2d(gy, gm, gd))


def jalali_to_gregorian(jy, jm, jd):
    """تبدیل تاریخ شمسی به میلادی — خروجی: (gy, gm, gd)"""
    return _d2g(_j2d(jy, jm, jd))


def jalali_weekday(jy, jm, jd):
    """روز هفته تاریخ شمسی — ۰=شنبه ... ۶=جمعه"""
    import datetime
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    d = datetime.date(gy, gm, gd)
    # در پایتون: دوشنبه=0 ... یکشنبه=6 | شنبه=5
    # (weekday+2)%7 → شنبه=0، یکشنبه=1، ... جمعه=6
    return (d.weekday() + 2) % 7


def fa_digits(text):
    """تبدیل ارقام لاتین به فارسی"""
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(text).translate(table)


def en_digits(text):
    """تبدیل ارقام فارسی/عربی به لاتین"""
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return str(text).translate(table)


def format_jalali(jy, jm, jd, month_name=False):
    """قالب‌بندی تاریخ شمسی"""
    if month_name:
        return f"{fa_digits(jd)} {JALALI_MONTHS[jm-1]} {fa_digits(jy)}"
    return f"{fa_digits(jy)}/{fa_digits(f'{jm:02d}')}/{fa_digits(f'{jd:02d}')}"


def tehran_today():
    """تاریخ امروز به وقت تهران — خروجی: (gy, gm, gd)"""
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=3, minutes=30))
    t = datetime.now(tz)
    return t.year, t.month, t.day


def today_jalali():
    """تاریخ امروز (به وقت تهران) به شمسی — خروجی: (jy, jm, jd)"""
    gy, gm, gd = tehran_today()
    return gregorian_to_jalali(gy, gm, gd)


def today_jalali_fa():
    """تاریخ امروز به شمسی با نام ماه و روز هفته"""
    jy, jm, jd = today_jalali()
    wd = WEEK_DAYS_FA[jalali_weekday(jy, jm, jd)]
    return f"{wd} {fa_digits(jd)} {JALALI_MONTHS[jm-1]} {fa_digits(jy)}"
