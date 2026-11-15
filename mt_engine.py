# -*- coding: utf-8 -*-
"""
موتور ترجمه ماشینی — پشتیبان «پیشنهاد ترجمه خودکار» پنل ادمین
--------------------------------------------------------------
بدون وابستگی خارجی (فقط کتابخانه استاندارد) با زنجیره تأمین چندسرویسی:

    1) google  — اندپوینت عمومی translate_a/single (بدون کلید، کیفیت بالا)
    2) lingva  — رابط متن‌باز گوگل ترنسلیت (بدون کلید؛ LINGVA_HOST قابل تنظیم)
    3) mymemory — سرویس رایگان MyMemory (محدودیت روزانه؛ با env بومی‌سازی)
    4) libre    — نمونه LibreTranslate در صورت تنظیم LIBRETRANSLATE_URL

تنظیمات محیطی اختیاری:
    MT_PROVIDER=auto|google|lingva|mymemory|libre   (پیش‌فرض: auto — به‌ترتیب بالا)
    MT_TIMEOUT=8                             (ثانیه؛ هر درخواست)
    LINGVA_HOST=https://lingva.garudalinux.org
    MYMEMORY_EMAIL=you@example.com           (سهمیه بیشتر MyMemory)
    LIBRETRANSLATE_URL=https://...           (فعال‌سازی LibreTranslate)
    LIBRETRANSLATE_API_KEY=...               (در صورت نیاز نمونه)
"""
import functools
import json
import os
import re
import urllib.parse
import urllib.request

TIMEOUT = int(os.environ.get("MT_TIMEOUT", "8"))

# نگاشت زبان‌های سامانه به کد هر سرویس
LANG_ALIASES = {
    "fa": {"google": "fa", "lingva": "fa", "mymemory": "fa-IR", "libre": "fa"},
    "en": {"google": "en", "lingva": "en", "mymemory": "en-GB", "libre": "en"},
    "ar": {"google": "ar", "lingva": "ar", "mymemory": "ar-SA", "libre": "ar"},
    "ru": {"google": "ru", "lingva": "ru", "mymemory": "ru-RU", "libre": "ru"},
    "zh": {"google": "zh-CN", "lingva": "zh", "mymemory": "zh-CN", "libre": "zh"},
}

PROVIDERS = ("google", "lingva", "mymemory", "libre")

_last_provider = None
_FAIL_STREAK = 0


def _order():
    pin = os.environ.get("MT_PROVIDER", "auto").strip().lower()
    if pin in PROVIDERS:
        return [pin]
    return list(PROVIDERS)


def last_provider():
    """نام سرویسی که آخرین ترجمه موفق را برگردانده"""
    return _last_provider


def fail_streak():
    """تعداد خطاهای پیاپی اخیر (برای توقف بهنگام کارهای گروهی)"""
    return _FAIL_STREAK


# ------------------------------------------------------------------
# ابزار شبکه
# ------------------------------------------------------------------
def _http_get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (rosecenter-mt/1.0)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


def _http_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"User-Agent": "Mozilla/5.0 (rosecenter-mt/1.0)",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


# ------------------------------------------------------------------
# تقسیم متن طولانی به قطعات قابل ارسال
# ------------------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[.!?؟…؛:])\s+")


def _chunks(text, limit):
    """تقسیم متن به قطعات ≤ limit با حفظ مرز جمله‌ها و پاراگراف‌ها"""
    out = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            out.append("")
            continue
        sents = [s for s in _SENT_SPLIT.split(para) if s]
        if not sents:
            sents = [para]
        cur = ""
        for s in sents:
            while len(s) > limit:  # جمله بسیار طولانی → برش سخت
                out.append(cur) if cur else None
                cur = ""
                out.append(s[:limit])
                s = s[limit:]
            if not cur:
                cur = s
            elif len(cur) + 1 + len(s) <= limit:
                cur += " " + s
            else:
                out.append(cur)
                cur = s
        if cur:
            out.append(cur)
    return out


def _join(parts, target):
    """اتصال ترجمه قطعات؛ برای زبان‌های بدون فاصله‌گذاری بدون جا"""
    sep = "" if target == "zh" else " "
    return "\n".join(p for p in parts if p != "" or True).replace(
        "\n\n", "\x00").replace("\n", sep).replace("\x00", "\n\n")


# ------------------------------------------------------------------
# سرویس‌های ترجمه
# ------------------------------------------------------------------
def _google(text, source, target):
    parts = []
    for ch in _chunks(text, 700):
        q = urllib.parse.urlencode(
            {"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": ch})
        raw = _http_get("https://translate.googleapis.com/translate_a/single?" + q)
        arr = json.loads(raw)
        seg = (arr or [None])[0] or []
        piece = "".join(s[0] for s in seg if s and s[0])
        if piece.strip():
            parts.append(piece)
    return _join(parts, target)


def _mymemory(text, source, target):
    email = os.environ.get("MYMEMORY_EMAIL", "").strip()
    parts = []
    for ch in _chunks(text, 450):
        q = urllib.parse.urlencode(
            {"q": ch, "langpair": f"{source}|{target}", **({"de": email} if email else {})})
        raw = _http_get("https://api.mymemory.translated.net/get?" + q)
        obj = json.loads(raw)
        out = (obj.get("responseData") or {}).get("translatedText") or ""
        if not out or "MYMEMORY WARNING" in out.upper() or "QUOTA" in out.upper():
            raise RuntimeError("mymemory quota/error")
        parts.append(out)
    return _join(parts, target)


def _libre(text, source, target):
    base = os.environ.get("LIBRETRANSLATE_URL", "").strip()
    if not base:
        raise RuntimeError("libre disabled (LIBRETRANSLATE_URL not set)")
    key = os.environ.get("LIBRETRANSLATE_API_KEY", "").strip()
    parts = []
    for ch in _chunks(text, 4000):
        payload = {"q": ch, "source": source, "target": target, "format": "text"}
        if key:
            payload["api_key"] = key
        raw = _http_post_json(base.rstrip("/") + "/translate", payload)
        obj = json.loads(raw)
        out = obj.get("translatedText") or ""
        if not out.strip():
            raise RuntimeError("libre empty")
        parts.append(out)
    return _join(parts, target)


def _lingva(text, source, target):
    """رابط متن‌باز Lingva (فرانت‌اند گوگل ترنسلیت بدون کلید)"""
    host = os.environ.get("LINGVA_HOST", "https://lingva.garudalinux.org").strip().rstrip("/")
    parts = []
    for ch in _chunks(text, 900):
        url = f"{host}/api/v1/{source}/{target}/{urllib.parse.quote(ch, safe='')}"
        raw = _http_get(url)
        obj = json.loads(raw)
        out = obj.get("translation") or ""
        if not out.strip():
            raise RuntimeError("lingva empty")
        parts.append(out)
    return _join(parts, target)


_HANDLERS = {"google": _google, "lingva": _lingva, "mymemory": _mymemory, "libre": _libre}


# ------------------------------------------------------------------
# کش و رابط عمومی
# ------------------------------------------------------------------
_MAX_CACHE = 2048
_CACHE = {}


@functools.lru_cache(maxsize=1)
def _noop():  # placeholder برای جلوگیری از هشدار linter
    return None


def translate(text, target, source="fa"):
    """ترجمه ماشینی متن فارسی به زبان هدف؛ در عدم موفقیت None برمی‌گرداند."""
    global _last_provider, _FAIL_STREAK
    src = (text or "").strip()
    if not src or target not in LANG_ALIASES or source not in LANG_ALIASES:
        return src or None
    # متن بدون هیچ حرف (عدد، نشانی وب و…) نیازی به ترجمه ندارد
    if not any(c.isalpha() for c in src):
        return src
    key = (src, source, target)
    if key in _CACHE:
        return _CACHE[key]
    for prov in _order():
        alias = LANG_ALIASES.get(source, {}).get(prov, source)
        talias = LANG_ALIASES.get(target, {}).get(prov, target)
        try:
            out = (_HANDLERS[prov])(src, alias, talias)
        except Exception:
            continue
        out = (out or "").strip()
        if out:
            _last_provider = prov
            _FAIL_STREAK = 0
            if len(_CACHE) < _MAX_CACHE:
                _CACHE[key] = out
            return out
    _FAIL_STREAK += 1
    return None
