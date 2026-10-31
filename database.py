# -*- coding: utf-8 -*-
"""لایه دسترسی به دیتابیس SQLite"""
import sqlite3
from flask import g
from config import DATABASE


def get_db():
    """اتصال به دیتابیس برای هر درخواست (ذخیره در context فلسک)"""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """بستن اتصال در پایان درخواست"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """ساخت جداول دیتابیس"""
    db = sqlite3.connect(DATABASE)
    c = db.cursor()

    # ---------- جدول تنظیمات ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        )
    """)

    # ---------- کاربران مدیریت ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name     TEXT NOT NULL DEFAULT 'مدیر سایت',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- خدمات ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            subtitle    TEXT NOT NULL DEFAULT '',
            summary     TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL DEFAULT '',
            icon        TEXT NOT NULL DEFAULT '',
            menu_order  INTEGER NOT NULL DEFAULT 0,
            is_visible  INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ---------- مراکز استانی ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS centers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            province      TEXT NOT NULL,
            clinic_name   TEXT NOT NULL DEFAULT '',
            address       TEXT NOT NULL DEFAULT '',
            postal_code   TEXT NOT NULL DEFAULT '',
            clinic_phone  TEXT NOT NULL DEFAULT '',
            manager_name  TEXT NOT NULL DEFAULT '',
            manager_phone TEXT NOT NULL DEFAULT '',
            exec_name     TEXT NOT NULL DEFAULT '',
            exec_phone    TEXT NOT NULL DEFAULT '',
            work_hours    TEXT NOT NULL DEFAULT '',
            map_url       TEXT NOT NULL DEFAULT '',
            is_soon       INTEGER NOT NULL DEFAULT 0,
            sort_order    INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ---------- اخبار و اطلاعیه‌ها ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            slug         TEXT UNIQUE NOT NULL,
            summary      TEXT NOT NULL DEFAULT '',
            content      TEXT NOT NULL DEFAULT '',
            category     TEXT NOT NULL DEFAULT 'اخبار',
            published    INTEGER NOT NULL DEFAULT 1,
            published_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            views        INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ---------- سوالات متداول ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL DEFAULT 'عمومی',
            question TEXT NOT NULL,
            answer   TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ---------- نظرات مراجعین (رضایت) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS testimonials (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            text     TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ---------- درخواست‌های نوبت مشاوره ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            full_name     TEXT NOT NULL,
            phone         TEXT NOT NULL,
            service_type  TEXT NOT NULL,
            center        TEXT NOT NULL DEFAULT '',
            note          TEXT NOT NULL DEFAULT '',
            status        TEXT NOT NULL DEFAULT 'در انتظار بررسی',
            admin_note    TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- درخواست‌های همکاری ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS cooperation_requests (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            full_name     TEXT NOT NULL,
            phone         TEXT NOT NULL,
            email         TEXT NOT NULL DEFAULT '',
            province      TEXT NOT NULL DEFAULT '',
            field         TEXT NOT NULL DEFAULT '',
            degree        TEXT NOT NULL DEFAULT '',
            experience    TEXT NOT NULL DEFAULT '',
            message       TEXT NOT NULL DEFAULT '',
            status        TEXT NOT NULL DEFAULT 'در انتظار بررسی',
            admin_note    TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- پیام‌های تماس با ما ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            phone      TEXT NOT NULL DEFAULT '',
            email      TEXT NOT NULL DEFAULT '',
            subject    TEXT NOT NULL DEFAULT '',
            message    TEXT NOT NULL,
            is_read    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- پیشنهادها و انتقادها ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL DEFAULT '',
            contact    TEXT NOT NULL DEFAULT '',
            kind       TEXT NOT NULL DEFAULT 'پیشنهاد',
            message    TEXT NOT NULL,
            is_read    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- دوره‌های آموزشی آکادمی رز ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            slug       TEXT UNIQUE NOT NULL,
            title      TEXT NOT NULL,
            summary    TEXT NOT NULL DEFAULT '',
            content    TEXT NOT NULL DEFAULT '',
            teacher    TEXT NOT NULL DEFAULT '',
            price      TEXT NOT NULL DEFAULT 'رایگان',
            duration   TEXT NOT NULL DEFAULT '',
            capacity   INTEGER NOT NULL DEFAULT 0,
            start_date TEXT NOT NULL DEFAULT '',
            schedule   TEXT NOT NULL DEFAULT '',
            level      TEXT NOT NULL DEFAULT 'عمومی',
            is_open    INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- ثبت‌نام‌های دوره‌ها ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS course_registrations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            course_id     INTEGER NOT NULL,
            first_name    TEXT NOT NULL,
            last_name     TEXT NOT NULL,
            national_code TEXT NOT NULL,
            mobile        TEXT NOT NULL,
            phone         TEXT NOT NULL DEFAULT '',
            email         TEXT NOT NULL DEFAULT '',
            education     TEXT NOT NULL DEFAULT '',
            city          TEXT NOT NULL DEFAULT '',
            note          TEXT NOT NULL DEFAULT '',
            status        TEXT NOT NULL DEFAULT 'در انتظار بررسی',
            admin_note    TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    """)

    # ---------- کاربران سایت (مشتریان/مراجعین) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            phone         TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            last_login_at TEXT NOT NULL DEFAULT ''
        )
    """)

    # ---------- سشن‌های لاگین‌شده (نمایش افراد آنلاین) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sid          TEXT UNIQUE NOT NULL,
            kind         TEXT NOT NULL DEFAULT 'user',
            user_id      INTEGER,
            display_name TEXT NOT NULL DEFAULT '',
            ip           TEXT NOT NULL DEFAULT '',
            user_agent   TEXT NOT NULL DEFAULT '',
            login_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            last_seen_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            logout_at    TEXT NOT NULL DEFAULT '',
            is_active    INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ---------- ستون‌های پروفایل SSO رز هاب (فاز ۶۵) ----------
    # انتقال مشخصات کامل کاربر در ورود یکپارچه: کد ملی، استان، کد استان و
    # کلینک محل خدمت. افزودن امن ستون — روی دیتابیس‌های قدیمی هم اجرا می‌شود.
    _user_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
    for _col in ("national_id", "province", "province_code", "clinic"):
        if _col not in _user_cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {_col} TEXT NOT NULL DEFAULT ''")

    # ---------- بلوک‌های دینامیک صفحه اصلی ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS home_blocks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kind       TEXT NOT NULL DEFAULT 'custom',
            title      TEXT NOT NULL,
            subtitle   TEXT NOT NULL DEFAULT '',
            icon       TEXT NOT NULL DEFAULT '✨',
            link       TEXT NOT NULL DEFAULT '',
            ref_id     INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_visible INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- کلیدهای API سامانه‌های خارجی ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            key           TEXT UNIQUE NOT NULL,
            is_active     INTEGER NOT NULL DEFAULT 1,
            note          TEXT NOT NULL DEFAULT '',
            request_count INTEGER NOT NULL DEFAULT 0,
            last_used_at  TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- فراخوان همکاری (فرم کامل مراکز مشاوره) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS hr_calls (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code     TEXT UNIQUE NOT NULL,
            first_name        TEXT NOT NULL,
            last_name         TEXT NOT NULL,
            national_code     TEXT NOT NULL,
            birth_date        TEXT NOT NULL DEFAULT '',
            gender            TEXT NOT NULL DEFAULT '',
            military_status   TEXT NOT NULL DEFAULT '',
            military_file     TEXT NOT NULL DEFAULT '',
            education_level   TEXT NOT NULL DEFAULT '',
            education_file    TEXT NOT NULL DEFAULT '',
            license_status    TEXT NOT NULL DEFAULT '',
            license_file      TEXT NOT NULL DEFAULT '',
            center_license_file TEXT NOT NULL DEFAULT '',
            license_desc      TEXT NOT NULL DEFAULT '',
            center_permit_file  TEXT NOT NULL DEFAULT '',
            ownership_status  TEXT NOT NULL DEFAULT '',
            property_file     TEXT NOT NULL DEFAULT '',
            province          TEXT NOT NULL DEFAULT '',
            county            TEXT NOT NULL DEFAULT '',
            center_phone      TEXT NOT NULL DEFAULT '',
            postal_code       TEXT NOT NULL DEFAULT '',
            full_address      TEXT NOT NULL DEFAULT '',
            individual_rooms  INTEGER NOT NULL DEFAULT 0,
            group_rooms       INTEGER NOT NULL DEFAULT 0,
            child_rooms       INTEGER NOT NULL DEFAULT 0,
            counselors_count  INTEGER NOT NULL DEFAULT 0,
            waiting_area      TEXT NOT NULL DEFAULT '',
            design_acceptance TEXT NOT NULL DEFAULT '',
            accessibility     TEXT NOT NULL DEFAULT '',
            mobile            TEXT NOT NULL DEFAULT '',
            national_card_file TEXT NOT NULL DEFAULT '',
            status            TEXT NOT NULL DEFAULT 'در انتظار بررسی',
            admin_note        TEXT NOT NULL DEFAULT '',
            created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- دسته‌بندی دوره‌ها (سبک مدرسه روان‌بُنه) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS course_categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            slug       TEXT UNIQUE NOT NULL,
            title      TEXT NOT NULL,
            icon       TEXT NOT NULL DEFAULT '📘',
            color      TEXT NOT NULL DEFAULT '#15803d',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_visible INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ---------- انجمن‌ها ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS forum_categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            icon        TEXT NOT NULL DEFAULT '💬',
            sort_order  INTEGER NOT NULL DEFAULT 0,
            is_visible  INTEGER NOT NULL DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS forum_topics (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id      INTEGER NOT NULL,
            user_id          INTEGER,
            author_name      TEXT NOT NULL DEFAULT '',
            title            TEXT NOT NULL,
            content          TEXT NOT NULL DEFAULT '',
            views            INTEGER NOT NULL DEFAULT 0,
            is_pinned        INTEGER NOT NULL DEFAULT 0,
            is_locked        INTEGER NOT NULL DEFAULT 0,
            is_visible       INTEGER NOT NULL DEFAULT 1,
            created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            last_activity_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (category_id) REFERENCES forum_categories(id) ON DELETE CASCADE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS forum_posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id    INTEGER NOT NULL,
            user_id     INTEGER,
            author_name TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL,
            is_visible  INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (topic_id) REFERENCES forum_topics(id) ON DELETE CASCADE
        )
    """)

    # ---------- مستندات چت هوشمند (پایگاه دانش) ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_documents (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            content    TEXT NOT NULL,
            keywords   TEXT NOT NULL DEFAULT '',
            link       TEXT NOT NULL DEFAULT '',
            link_label TEXT NOT NULL DEFAULT '',
            category   TEXT NOT NULL DEFAULT 'عمومی',
            priority   INTEGER NOT NULL DEFAULT 0,
            hit_count  INTEGER NOT NULL DEFAULT 0,
            is_active  INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- لاگ گفتگوهای چت ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key  TEXT NOT NULL DEFAULT '',
            user_id      INTEGER,
            question     TEXT NOT NULL,
            answer       TEXT NOT NULL DEFAULT '',
            matched_doc  TEXT NOT NULL DEFAULT '',
            score        REAL NOT NULL DEFAULT 0,
            is_answered  INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- اعضای هیئت مدیره ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS board_members (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name  TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'عضو هیئت مدیره',
            bio        TEXT NOT NULL DEFAULT '',
            photo      TEXT NOT NULL DEFAULT '',
            skills     TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_visible INTEGER NOT NULL DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS slides (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            subtitle     TEXT NOT NULL DEFAULT '',
            image        TEXT NOT NULL DEFAULT '',
            link         TEXT NOT NULL DEFAULT '',
            button_label TEXT NOT NULL DEFAULT 'مشاهده بیشتر',
            sort_order   INTEGER NOT NULL DEFAULT 0,
            is_visible   INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ---------- مایگریشن‌های سبک (ستون‌های اضافه‌شده در نسخه‌های بعد) ----------
    def _add_column(table, col_sql):
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        name = col_sql.split()[0]
        if name not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col_sql}")

    _add_column("bookings", "source TEXT NOT NULL DEFAULT 'وب‌سایت'")
    _add_column("bookings", "user_id INTEGER")
    _add_column("bookings", "api_key_id INTEGER")
    _add_column("course_registrations", "user_id INTEGER")
    _add_column("hr_calls", "user_id INTEGER")

    # گسترش دوره‌ها (نسخه LMS)
    _add_column("courses", "category_id INTEGER")
    _add_column("courses", "status TEXT NOT NULL DEFAULT 'registration'")
    _add_column("courses", "rating REAL NOT NULL DEFAULT 4.5")
    _add_column("courses", "votes INTEGER NOT NULL DEFAULT 0")
    _add_column("courses", "students INTEGER NOT NULL DEFAULT 0")
    _add_column("courses", "price_num INTEGER NOT NULL DEFAULT 0")
    _add_column("courses", "is_free INTEGER NOT NULL DEFAULT 0")
    _add_column("courses", "is_special INTEGER NOT NULL DEFAULT 0")
    _add_column("courses", "thumb TEXT NOT NULL DEFAULT ''")

    # گسترش مراکز (ثبت مراکز و کلینیک‌ها + نقشه)
    _add_column("centers", "kind TEXT NOT NULL DEFAULT 'مرکز استانی'")
    _add_column("centers", "lat REAL")
    _add_column("centers", "lng REAL")
    _add_column("centers", "capabilities TEXT NOT NULL DEFAULT ''")
    _add_column("centers", "is_approved INTEGER NOT NULL DEFAULT 1")
    _add_column("centers", "submitter_name TEXT NOT NULL DEFAULT ''")
    _add_column("centers", "submitter_phone TEXT NOT NULL DEFAULT ''")
    _add_column("centers", "email TEXT NOT NULL DEFAULT ''")
    _add_column("centers", "website TEXT NOT NULL DEFAULT ''")

    db.commit()
    db.close()


def query(sql, args=(), one=False):
    """اجرای کوئری SELECT و برگرداندن نتیجه"""
    from flask import current_app
    db = get_db()
    cur = db.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    """اجرای کوئری INSERT/UPDATE/DELETE"""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
