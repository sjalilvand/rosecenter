"""لایه دسترسی به دیتابیس SQLite"""
import sqlite3
from flask import g, current_app


def get_db():
    """اتصال به دیتابیس (در طول یک درخواست فقط یک اتصال ساخته می‌شود)"""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    """اجرای کوئری SELECT و برگرداندن نتایج"""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """اجرای کوئری INSERT/UPDATE/DELETE با commit خودکار"""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def count(table, where='1=1', params=()):
    row = query(f"SELECT COUNT(*) AS c FROM {table} WHERE {where}", params, one=True)
    return row['c'] if row else 0
