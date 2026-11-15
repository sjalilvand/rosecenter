# -*- coding: utf-8 -*-
"""
ترجمه چندزبانه محتوای دیتابیس — نسخه ۳
محتوای فارسی متن پایه است (در ستون‌های جدول‌ها) و ترجمه‌های
English / العربية / Русский / 中文 در جدول translations نگهداری می‌شوند.

- ثبت ترجمه از پنل ادمین: فرم‌های خبر/دوره + صفحه اختصاصی «ترجمه محتوا»
- نمایش در سایت: هر فیلد ترجمه‌شده بر متن فارسی سوار می‌شود (fallback: فارسی)
- وب‌سرویس API v1: پارامتر ?lang=en|ar|ru|zh روی همه اندپوینت‌های محتوایی
"""
import database

# زبان‌های قابل ترجمه (فارسی = متن پایه، ترجمه نمی‌خواهد)
TARGET_LANGS = ("en", "ar", "ru", "zh")

# فهرست جداول و فیلدهای قابل ترجمه — «title_col» ستونی است که در
# فهرست مدیریتی به‌عنوان عنوان آیتم نمایش داده می‌شود.
TRANSLATABLE = {
    "services":          {"label": "خدمات",              "fields": ["title", "subtitle", "summary", "content"], "title_col": "title"},
    "news":              {"label": "اخبار",              "fields": ["title", "summary", "content"],             "title_col": "title"},
    "courses":           {"label": "دوره‌های آموزشی",     "fields": ["title", "summary", "content", "teacher"],  "title_col": "title"},
    "course_categories": {"label": "دسته‌بندی دوره‌ها",   "fields": ["title"],                                   "title_col": "title"},
    "faqs":              {"label": "سوالات متداول",       "fields": ["question", "answer"],                      "title_col": "question"},
    "testimonials":      {"label": "نظرات مراجعین",       "fields": ["name", "text"],                            "title_col": "name"},
    "home_blocks":       {"label": "بلوک‌های صفحه اصلی",  "fields": ["title", "subtitle"],                       "title_col": "title"},
    "slides":            {"label": "اسلایدر صفحه اصلی",   "fields": ["title", "subtitle", "button_label"],       "title_col": "title"},
    "board_members":     {"label": "هیئت مدیره",          "fields": ["full_name", "role", "bio"],                "title_col": "full_name"},
    "centers":           {"label": "مراکز و کلینیک‌ها",   "fields": ["province", "clinic_name", "address", "work_hours"], "title_col": "province"},
    "forum_categories":  {"label": "انجمن‌ها",            "fields": ["title", "description"],                    "title_col": "title"},
}

# برچسب فیلدها برای نمایش در پنل ادمین
FIELD_LABELS = {
    "title":        "عنوان",
    "subtitle":     "زیرعنوان",
    "summary":      "خلاصه",
    "content":      "متن کامل",
    "teacher":      "مدرس",
    "question":     "پرسش",
    "answer":       "پاسخ",
    "name":         "نام",
    "text":         "متن",
    "button_label": "متن دکمه",
    "full_name":    "نام و نام خانوادگی",
    "role":         "سمت",
    "bio":          "بیوگرافی",
    "province":     "استان",
    "clinic_name":  "نام کلینیک / مرکز",
    "address":      "نشانی",
    "work_hours":   "ساعات کاری",
    "description":  "توضیحات",
}


def is_translatable(table):
    return table in TRANSLATABLE


# ------------------------------------------------------------------
# خواندن ترجمه‌ها
# ------------------------------------------------------------------
def get_map(table, row_ids, lang):
    """نقشه {(row_id, field): value} برای یک زبان مشخص"""
    ids = [int(i) for i in row_ids if i]
    if not ids or lang not in TARGET_LANGS or not is_translatable(table):
        return {}
    marks = ",".join("?" * len(ids))
    rows = database.query(
        f"""SELECT row_id, field, value FROM translations
            WHERE table_name=? AND lang=? AND value!='' AND row_id IN ({marks})""",
        (table, lang, *ids))
    return {(r["row_id"], r["field"]): r["value"] for r in rows}


def get_map_multi(table, row_ids, langs=TARGET_LANGS):
    """نقشه {(row_id, lang, field): value} برای چند زبان (پنل ادمین)"""
    ids = [int(i) for i in row_ids if i]
    if not ids or not is_translatable(table):
        return {}
    marks = ",".join("?" * len(ids))
    lmarks = ",".join("?" * len(langs))
    rows = database.query(
        f"""SELECT row_id, lang, field, value FROM translations
            WHERE table_name=? AND value!='' AND lang IN ({lmarks})
            AND row_id IN ({marks})""",
        (table, *langs, *ids))
    return {(r["row_id"], r["lang"], r["field"]): r["value"] for r in rows}


def get_all_for(table, row_id):
    """همه ترجمه‌های یک ردیف — {(lang, field): value}"""
    if not is_translatable(table):
        return {}
    rows = database.query(
        "SELECT lang, field, value FROM translations WHERE table_name=? AND row_id=? AND value!=''",
        (table, int(row_id)))
    return {(r["lang"], r["field"]): r["value"] for r in rows}


# ------------------------------------------------------------------
# سوار کردن ترجمه روی نتایج کوئری (نمایش در سایت)
# ------------------------------------------------------------------
def apply(table, rows, locale):
    """اعمال ترجمه یک جدول روی فهرست نتایج؛ برای فارسی بدون تغییر برمی‌گردد"""
    if locale not in TARGET_LANGS or not rows or not is_translatable(table):
        return rows
    tmap = get_map(table, [r["id"] for r in rows], locale)
    if not tmap:
        return rows
    fields = TRANSLATABLE[table]["fields"]
    out = []
    for r in rows:
        d = dict(r)
        rid = d.get("id")
        if rid is not None:
            for field in fields:
                v = tmap.get((rid, field))
                if v:
                    d[field] = v
        out.append(d)
    return out


def apply_one(table, row, locale):
    """نسخه تک‌ردیفی apply"""
    if row is None:
        return row
    return apply(table, [row], locale)[0]


# ------------------------------------------------------------------
# ذخیره و حذف
# ------------------------------------------------------------------
def save_from_form(table, row_id, form):
    """ذخیره ترجمه‌ها از فرم ادمین؛ فیلدها با نام tr_<lang>_<field> می‌آیند.
    فیلد خالی یعنی حذف ترجمه (بازگشت به متن فارسی پایه)."""
    if not is_translatable(table):
        return 0
    fields = TRANSLATABLE[table]["fields"]
    saved = 0
    for lang in TARGET_LANGS:
        for field in fields:
            raw = form.get(f"tr_{lang}_{field}")
            if raw is None:
                continue
            value = raw.strip()
            existing = database.query(
                "SELECT id, value FROM translations WHERE table_name=? AND row_id=? AND field=? AND lang=?",
                (table, int(row_id), field, lang), one=True)
            if value:
                if existing:
                    database.execute(
                        """UPDATE translations SET value=?, updated_at=datetime('now','localtime')
                           WHERE id=?""", (value, existing["id"]))
                else:
                    database.execute(
                        """INSERT INTO translations (table_name, row_id, field, lang, value)
                           VALUES (?,?,?,?,?)""", (table, int(row_id), field, lang, value))
                saved += 1
            elif existing:
                database.execute("DELETE FROM translations WHERE id=?", (existing["id"],))
                saved += 1
    return saved


def set_translation(table, row_id, lang, field, value):
    """ثبت/به‌روزرسانی مستقیم یک ترجمه (برای درج ماشینی گروهی)؛ مقدار خالی = حذف"""
    if not is_translatable(table) or lang not in TARGET_LANGS:
        return False
    if field not in TRANSLATABLE[table]["fields"]:
        return False
    value = (value or "").strip()
    existing = database.query(
        "SELECT id FROM translations WHERE table_name=? AND row_id=? AND field=? AND lang=?",
        (table, int(row_id), field, lang), one=True)
    if value:
        if existing:
            database.execute(
                "UPDATE translations SET value=?, updated_at=datetime('now','localtime') WHERE id=?",
                (value, existing["id"]))
        else:
            database.execute(
                "INSERT INTO translations (table_name, row_id, field, lang, value) VALUES (?,?,?,?,?)",
                (table, int(row_id), field, lang, value))
        return True
    if existing:
        database.execute("DELETE FROM translations WHERE id=?", (existing["id"],))
        return True
    return False


def delete_row(table, row_id):
    """پاک‌سازی ترجمه‌های یک ردیف هنگام حذف آن"""
    if not is_translatable(table):
        return
    database.execute(
        "DELETE FROM translations WHERE table_name=? AND row_id=?", (table, int(row_id)))


# ------------------------------------------------------------------
# آمار پوشش ترجمه برای صفحه مدیریتی
# ------------------------------------------------------------------
def coverage(table):
    """برای هر ردیف: {row_id: {lang: filled_fields_count}}"""
    if not is_translatable(table):
        return {}
    rows = database.query(
        """SELECT row_id, lang, COUNT(*) n FROM translations
           WHERE table_name=? AND value!='' AND lang IN ('en','ar','ru','zh')
           GROUP BY row_id, lang""", (table,))
    out = {}
    for r in rows:
        out.setdefault(r["row_id"], {})[r["lang"]] = r["n"]
    return out
