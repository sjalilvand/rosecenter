# -*- coding: utf-8 -*-
"""
درج ترجمه‌های چهارزبانه (EN/AR/RU/ZH) محتوای دیتابیس — idempotent
----------------------------------------------------------------
- ترجمه‌های دستی دقیق محتوای نمونه: seed_content_a.py + seed_content_b.py
  (خدمات، اخبار، اسلایدر، بلوک‌ها، دوره‌ها، نظرات، ۳۱ مرکز، سوالات متداول)
- یافتن ردیف بر اساس «متن فارسی» (مستقل از id) و اعمال روی همه ردیف‌های منطبق
- هرگز ترجمه موجود را بازنویسی نمی‌کند (فقط فیلد خالی پر می‌شود)

اجرا:
    python seed_translations.py            → فقط ترجمه‌های دستی
    python seed_translations.py --auto     → + ترجمه ماشینی بقیه فیلدهای خالی
    python seed_translations.py --dry-run  → فقط گزارش، بدون تغییر
"""
import sys
import sqlite3
import argparse
from config import DATABASE

import mt_engine
from seed_content_a import SEEDS_A
from seed_content_b import SEEDS_B, SEEDS_FAQ

SEEDS = SEEDS_A + SEEDS_B + [{"table": "faqs", **e} for e in SEEDS_FAQ]

# جدول‌های قابل ترجمه — همان تعریف content_i18n (بدون import فلسکی)
TRANSLATABLE = {
    "services":          ["title", "subtitle", "summary", "content"],
    "news":              ["title", "summary", "content"],
    "courses":           ["title", "summary", "content", "teacher"],
    "course_categories": ["title"],
    "faqs":              ["question", "answer"],
    "testimonials":      ["name", "text"],
    "home_blocks":       ["title", "subtitle"],
    "slides":            ["title", "subtitle", "button_label"],
    "board_members":     ["full_name", "role", "bio"],
    "centers":           ["province", "clinic_name", "address", "work_hours"],
    "forum_categories":  ["title", "description"],
}
TARGET_LANGS = ("en", "ar", "ru", "zh")


def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL, row_id INTEGER NOT NULL,
        field TEXT NOT NULL, lang TEXT NOT NULL,
        value TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_translations_uniq "
               "ON translations(table_name, row_id, field, lang)")
    db.commit()
    return db


def find_rows(db, table, src):
    """یافتن ردیف‌های منطبق با متن فارسی مرجع"""
    keys = list(src.keys())
    if not keys:
        return []
    where = " AND ".join(f"{k} = ?" for k in keys)
    try:
        return db.execute(f"SELECT id FROM {table} WHERE {where}",
                          tuple(src[k] for k in keys)).fetchall()
    except sqlite3.OperationalError:
        return []


def upsert(db, table, rid, lang, field, value):
    """درج ترجمه؛ اگر مقدار غیرخالی موجود باشد دست نمی‌زند"""
    row = db.execute(
        "SELECT id, value FROM translations WHERE table_name=? AND row_id=? AND field=? AND lang=?",
        (table, rid, field, lang)).fetchone()
    value = (value or "").strip()
    if row and (row["value"] or "").strip():
        return "kept"
    if row:
        db.execute("UPDATE translations SET value=?, updated_at=datetime('now','localtime') WHERE id=?",
                   (value, row["id"]))
        return "updated" if value else "deleted"
    if value:
        db.execute("INSERT INTO translations (table_name, row_id, field, lang, value) VALUES (?,?,?,?,?)",
                   (table, rid, field, lang, value))
        return "inserted"
    return "none"


def seed_manual(db, dry=False):
    """درج ترجمه‌های دستی"""
    ins = upd = kept = miss = 0
    for e in SEEDS:
        table, src, tr = e["table"], e["src"], e["tr"]
        rows = find_rows(db, table, src)
        if not rows:
            miss += 1
            print(f"  ⚠ ردیف مرجع یافت نشد: {table} — {list(src.values())[0][:60]}")
            continue
        for r in rows:
            # متن پایه فیلد باید غیرخالی باشد
            base = db.execute(f"SELECT * FROM {table} WHERE id=?", (r["id"],)).fetchone()
            for lg, fv in tr.items():
                for f, val in fv.items():
                    if f not in base.keys() or not (base[f] or "").strip():
                        continue
                    res = "inserted" if not dry else "dry"
                    if not dry:
                        res = upsert(db, table, r["id"], lg, f, val)
                    if res in ("inserted", "updated", "dry"):
                        ins += 1
                    elif res == "kept":
                        kept += 1
    db.commit()
    return ins, kept, miss


def seed_auto(db, dry=False, stop_after=10):
    """ترجمه ماشینی بقیه فیلدهای خالی همه جدول‌های قابل ترجمه"""
    total_ins = 0
    fails = 0
    for table, fields in TRANSLATABLE.items():
        try:
            rows = db.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            if mt_engine.fail_streak() >= stop_after:
                print(f"  ✋ {stop_after} خطای پیاپی در سرویس ترجمه — بخش ماشینی متوقف شد (بعداً دوباره اجرا کنید)")
                return total_ins
            for f in fields:
                if f not in row.keys():
                    continue
                src = (row[f] or "").strip()
                if not src:
                    continue
                for lg in TARGET_LANGS:
                    ex = db.execute(
                        "SELECT value FROM translations WHERE table_name=? AND row_id=? AND field=? AND lang=?",
                        (table, row["id"], f, lg)).fetchone()
                    if ex and (ex["value"] or "").strip():
                        continue
                    if dry:
                        total_ins += 1
                        continue
                    tr = mt_engine.translate(src, lg)
                    if tr:
                        upsert(db, table, row["id"], lg, f, tr)
                        total_ins += 1
                    else:
                        fails += 1
            db.commit()
    return total_ins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="ترجمه ماشینی فیلدهای خالی باقی‌مانده")
    ap.add_argument("--dry-run", action="store_true", help="بدون تغییر؛ فقط گزارش")
    args = ap.parse_args()

    db = connect()
    print("== درج ترجمه‌های دستی ==")
    ins, kept, miss = seed_manual(db, dry=args.dry_run)
    print(f"   درج/به‌روزرسانی: {ins} — حفظ ترجمه موجود: {kept} — مرجع گمشده: {miss}")

    if args.auto:
        print("== ترجمه ماشینی فیلدهای خالی ==")
        n = seed_auto(db, dry=args.dry_run)
        print(f"   ترجمه ماشینی درج‌شده: {n}")

    n_tr = db.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    print(f"جمع کل ترجمه‌ها در جدول translations: {n_tr}")
    if not args.dry_run:
        print("تمام شد ✅")


if __name__ == "__main__":
    main()
