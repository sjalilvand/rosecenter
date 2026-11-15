#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بازنشانی رمز مدیر سایت / ساخت مدیر جدید — کلینیک رز

مثال‌ها:
    python tools/reset_admin.py --list                        # فهرست مدیرها
    python tools/reset_admin.py -u admin -p "رمز-جدید"        # بازنشانی رمز «admin»
    python tools/reset_admin.py -u admin                      # رمز تصادفیِ قوی می‌سازد و چاپ می‌کند
    python tools/reset_admin.py -u manager2 -p "رمز" --create # ساخت مدیر جدید
"""
import argparse
import os
import secrets
import sqlite3
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
from config import DATABASE  # noqa: E402
from werkzeug.security import generate_password_hash, check_password_hash  # noqa: E402

SYMBOLS = "!@#$%^&*-"


def gen_password(n=14):
    """ساخت رمز قوی تصادفی با حداقل یک حرف کوچک/بزرگ/رقم/نماد"""
    alphabet = string.ascii_letters + string.digits + SYMBOLS
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(n))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in SYMBOLS for c in pw)
        ):
            return pw


def main():
    ap = argparse.ArgumentParser(description="بازنشانی رمز مدیر کلینیک رز")
    ap.add_argument("-u", "--username", default="admin", help="نام کاربری مدیر (پیش‌فرض: admin)")
    ap.add_argument("-p", "--password", default=None, help="رمز جدید؛ اگر ندهید رمز قوی تصادفی ساخته می‌شود")
    ap.add_argument("--create", action="store_true", help="به‌جای بازنشانی، یک مدیر جدید بساز")
    ap.add_argument("--list", action="store_true", help="فهرست مدیرهای فعلی")
    ap.add_argument("--check-only", action="store_true", help="فقط بررسی رمز داده‌شده در -p بدون تغییر (تست ورود)")
    args = ap.parse_args()

    # ساخت جداول در صورت نبود دیتابیس (مثل seed_data.py)
    database.init_db(None)

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    if args.list:
        rows = c.execute(
            "SELECT username, full_name, created_at FROM admin_users ORDER BY id"
        ).fetchall()
        if not rows:
            print("هیچ مدیری ثبت نشده است.")
        for r in rows:
            print("- {username}  |  {full_name}  |  ساخته‌شده: {created_at}".format(**r))
        return

    if args.check_only:
        row = c.execute(
            "SELECT * FROM admin_users WHERE username=?", (args.username,)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], args.password or ""):
            print("OK: رمز درست است.")
        else:
            print("NO: نام کاربری یا رمز نادرست است.")
            sys.exit(1)
        return

    pw = args.password or gen_password()
    if len(pw) < 8:
        print("خطا: رمز عبور باید حداقل ۸ نویسه باشد.")
        sys.exit(1)

    row = c.execute("SELECT * FROM admin_users WHERE username=?", (args.username,)).fetchone()

    if args.create:
        if row:
            print("خطا: نام کاربری «{0}» از قبل وجود دارد؛ برای تغییر رمزش از --create استفاده نکنید.".format(args.username))
            sys.exit(1)
        c.execute(
            "INSERT INTO admin_users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (args.username, generate_password_hash(pw), "مدیر"),
        )
        db.commit()
        print("مدیر جدید ساخته شد.")
    elif row:
        c.execute(
            "UPDATE admin_users SET password_hash=? WHERE id=?",
            (generate_password_hash(pw), row["id"]),
        )
        db.commit()
        print("رمز مدیر «{0}» بازنشانی شد.".format(args.username))
    else:
        c.execute(
            "INSERT INTO admin_users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (args.username, generate_password_hash(pw), "مدیر کلینیک رز"),
        )
        db.commit()
        print("مدیر «{0}» پیدا نشد؛ به‌صورت جدید ساخته شد.".format(args.username))

    print()
    print("  نشانی پنل ادمین : http://127.0.0.1:8083/admin/login")
    print("  نام کاربری      : {0}".format(args.username))
    print("  رمز عبور        : {0}".format(pw))
    print()
    print("  این رمز را در جای امن ذخیره کنید. داخل پنل هم می‌توانید از بخش تغییر رمز، آن را عوض کنید.")


if __name__ == "__main__":
    main()
