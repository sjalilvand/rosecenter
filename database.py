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
