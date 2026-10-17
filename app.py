# -*- coding: utf-8 -*-
"""
وب‌سایت مرکز خدمات روانشناسی و مشاوره رز
بازنویسی کامل با Flask + SQLite
"""
import os
import secrets
import string
import math
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, g, jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash

import database
from config import THERAPY_TYPES, REQUEST_STATUSES

app = Flask(__name__)
app.config.from_object("config")

database.init_db(app)

# اتصال خودکار به دیتابیس در هر درخواست
def _ensure_db():
    database.get_db()


app.before_request(_ensure_db)
app.teardown_appcontext(database.close_db)

PER_PAGE = 9  # تعداد اخبار در هر صفحه


# ------------------------------------------------------------------
# ابزارهای کمکی
# ------------------------------------------------------------------
def gen_tracking_code(prefix="RC"):
    """تولید کد پیگیری یکتا"""
    chars = string.digits + string.ascii_uppercase
    code = "".join(secrets.choice(chars) for _ in range(8))
    return f"{prefix}-{code}"


def csrf_token():
    """توکن CSRF برای فرم‌ها"""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["THERAPY_TYPES"] = THERAPY_TYPES


def valid_csrf():
    tok = request.form.get("_csrf", "")
    return tok and tok == session.get("_csrf")


def get_settings():
    """خواندن تنظیمات سایت (کش در هر درخواست)"""
    if "settings" not in g:
        rows = database.query("SELECT key, value FROM settings")
        g.settings = {r["key"]: r["value"] for r in rows}
    return g.settings


def get_visible_services():
    return database.query("SELECT * FROM services WHERE is_visible=1 ORDER BY menu_order")


@app.context_processor
def inject_globals():
    return {
        "settings": get_settings(),
        "nav_services": get_visible_services(),
        "REQUEST_STATUSES": REQUEST_STATUSES,
    }


# ------------------------------------------------------------------
# دکوراتور ورود مدیریت
# ------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_csrf(f):
    """بررسی CSRF برای فرم‌های پنل مدیریت"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == "POST" and not valid_csrf():
            abort(400, "درخواست نامعتبر است (CSRF)")
        return f(*args, **kwargs)
    return wrapper


# ==================================================================
# صفحات عمومی
# ==================================================================
@app.route("/")
def home():
    services = get_visible_services()
    testimonials = database.query("SELECT * FROM testimonials ORDER BY sort_order")
    faqs = database.query("SELECT * FROM faqs ORDER BY sort_order")
    centers = database.query("SELECT id, province FROM centers WHERE is_soon=0 ORDER BY sort_order")
    return render_template("home.html", services=services, testimonials=testimonials,
                           faqs=faqs, centers=centers, page_title="خانه")


@app.route("/psychotherapy/")
@app.route("/consulting/")
@app.route("/education/")
@app.route("/other-services/")
def service_page():
    slug = request.path.strip("/")
    svc = database.query("SELECT * FROM services WHERE slug=? AND is_visible=1", (slug,), one=True)
    if not svc:
        abort(404)
    faqs = database.query("SELECT * FROM faqs ORDER BY sort_order")
    return render_template("service.html", svc=svc, faqs=faqs, page_title=svc["title"])


@app.route("/services/")
def services_index():
    services = get_visible_services()
    return render_template("services_index.html", services=services, page_title="خدمات ما")


@app.route("/centers/")
@app.route("/مراکز-استانی/")
def centers():
    q = request.args.get("q", "").strip()
    sql = "SELECT * FROM centers"
    args = ()
    if q:
        sql += " WHERE province LIKE ? OR address LIKE ?"
        args = (f"%{q}%", f"%{q}%")
    sql += " ORDER BY is_soon, sort_order"
    rows = database.query(sql, args)
    return render_template("centers.html", centers=rows, q=q, page_title="مراکز استانی")


@app.route("/cooperation/", methods=["GET", "POST"])
def cooperation():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        name = f.get("full_name", "").strip()
        phone = f.get("phone", "").strip()
        if not name or not phone:
            flash("نام و شماره تماس الزامی است.", "error")
            return redirect(url_for("cooperation"))
        code = gen_tracking_code("HR")
        database.execute(
            """INSERT INTO cooperation_requests
            (tracking_code, full_name, phone, email, province, field, degree, experience, message)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (code, name, phone, f.get("email", "").strip(), f.get("province", "").strip(),
             f.get("field", "").strip(), f.get("degree", "").strip(),
             f.get("experience", "").strip(), f.get("message", "").strip()),
        )
        flash(f"درخواست همکاری شما با موفقیت ثبت شد. کد پیگیری: {code}", "success")
        session["last_code"] = code
        return redirect(url_for("cooperation"))
    provinces = database.query("SELECT province FROM centers ORDER BY sort_order")
    return render_template("cooperation.html", provinces=provinces, page_title="درخواست همکاری")


@app.route("/academy/")
def academy():
    return render_template("academy.html", page_title="آکادمی رز")


@app.route("/news/")
@app.route("/news-articles/")
def news_list():
    q = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    where, args = "WHERE published=1", ()
    if q:
        where += " AND (title LIKE ? OR summary LIKE ?)"
        args = (f"%{q}%", f"%{q}%")
    total = database.query(f"SELECT COUNT(*) AS n FROM news {where}", args, one=True)["n"]
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, pages)
    rows = database.query(
        f"SELECT * FROM news {where} ORDER BY published_at DESC, id DESC LIMIT ? OFFSET ?",
        (*args, PER_PAGE, (page - 1) * PER_PAGE),
    )
    return render_template("news.html", news=rows, q=q, page=page, pages=pages,
                           total=total, page_title="اخبار و اطلاعیه‌ها")


@app.route("/news/<slug>/")
def news_detail(slug):
    row = database.query("SELECT * FROM news WHERE slug=? AND published=1", (slug,), one=True)
    if not row:
        abort(404)
    database.execute("UPDATE news SET views=views+1 WHERE id=?", (row["id"],))
    related = database.query(
        "SELECT * FROM news WHERE published=1 AND id!=? ORDER BY published_at DESC LIMIT 3",
        (row["id"],),
    )
    return render_template("news_detail.html", item=row, related=related,
                           page_title=row["title"])


@app.route("/about/")
def about():
    return render_template("about.html", page_title="درباره ما")


@app.route("/contact/", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        name = f.get("name", "").strip()
        message = f.get("message", "").strip()
        if not name or not message:
            flash("نام و متن پیام الزامی است.", "error")
            return redirect(url_for("contact"))
        database.execute(
            "INSERT INTO contact_messages (name, phone, email, subject, message) VALUES (?,?,?,?,?)",
            (name, f.get("phone", "").strip(), f.get("email", "").strip(),
             f.get("subject", "").strip(), message),
        )
        flash("پیام شما با موفقیت ارسال شد. به‌زودی با شما تماس می‌گیریم.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html", page_title="تماس با ما")


@app.route("/consultation/", methods=["GET", "POST"])
def consultation():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        name = f.get("full_name", "").strip()
        phone = f.get("phone", "").strip()
        service_type = f.get("service_type", "").strip()
        if not name or not phone or not service_type:
            flash("لطفاً نام، شماره تماس و نوع درمان را انتخاب کنید.", "error")
            return redirect(url_for("consultation"))
        code = gen_tracking_code("RC")
        database.execute(
            """INSERT INTO bookings (tracking_code, full_name, phone, service_type, center, note)
            VALUES (?,?,?,?,?,?)""",
            (code, name, phone, service_type, f.get("center", "").strip(), f.get("note", "").strip()),
        )
        flash(f"درخواست نوبت شما با موفقیت ثبت شد. کد پیگیری شما: {code}", "success")
        session["last_code"] = code
        return redirect(url_for("consultation"))
    centers = database.query("SELECT province FROM centers WHERE is_soon=0 ORDER BY sort_order")
    return render_template("consultation.html", centers=centers, page_title="درخواست مشاوره")


@app.route("/tracking/", methods=["GET", "POST"])
def tracking():
    result = None
    kind = None
    code = request.values.get("code", "").strip().upper()
    if code:
        result = database.query(
            "SELECT tracking_code, full_name, service_type, status, admin_note, created_at FROM bookings WHERE tracking_code=?",
            (code,), one=True,
        )
        kind = "booking"
        if not result:
            result = database.query(
                "SELECT tracking_code, full_name, field AS service_type, status, admin_note, created_at FROM cooperation_requests WHERE tracking_code=?",
                (code,), one=True,
            )
            kind = "cooperation"
        if not result:
            flash("درخواستی با این کد پیگیری یافت نشد. لطفاً کد را بررسی کنید.", "error")
    return render_template("tracking.html", result=result, kind=kind, code=code,
                           page_title="پیگیری درخواست")


@app.route("/feedback/", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        message = request.form.get("message", "").strip()
        if not message:
            flash("متن پیام الزامی است.", "error")
            return redirect(url_for("feedback"))
        database.execute(
            "INSERT INTO feedbacks (name, contact, kind, message) VALUES (?,?,?,?)",
            (request.form.get("name", "").strip(), request.form.get("contact", "").strip(),
             request.form.get("kind", "پیشنهاد"), message),
        )
        flash("نظر شما با موفقیت ثبت شد. از همراهی شما سپاسگزاریم.", "success")
        return redirect(url_for("feedback"))
    return render_template("feedback.html", page_title="پیشنهاد و انتقاد")


@app.route("/search/")
def search():
    q = request.args.get("q", "").strip()
    results = {"services": [], "news": [], "faqs": [], "centers": []}
    if q:
        like = f"%{q}%"
        results["services"] = database.query(
            "SELECT slug, title, summary FROM services WHERE is_visible=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",
            (like, like, like))
        results["news"] = database.query(
            "SELECT slug, title, summary, published_at FROM news WHERE published=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",
            (like, like, like))
        results["faqs"] = database.query(
            "SELECT id, question, answer FROM faqs WHERE question LIKE ? OR answer LIKE ? LIMIT 10",
            (like, like))
        results["centers"] = database.query(
            "SELECT province, address, clinic_phone FROM centers WHERE province LIKE ? OR address LIKE ?",
            (like, like))
    return render_template("search.html", q=q, results=results, page_title="جستجو")


# ==================================================================
# پنل مدیریت
# ==================================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        u = database.query(
            "SELECT * FROM admin_users WHERE username=?", (request.form.get("username", ""),), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session["admin_id"] = u["id"]
            session["admin_name"] = u["full_name"]
            session.permanent = True
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("نام کاربری یا گذرواژه نادرست است.", "error")
    return render_template("admin/login.html", page_title="ورود مدیریت")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/")
@admin_required
def admin_dashboard():
    stats = {
        "bookings": database.query("SELECT COUNT(*) n FROM bookings", one=True)["n"],
        "bookings_new": database.query("SELECT COUNT(*) n FROM bookings WHERE status='در انتظار بررسی'", one=True)["n"],
        "cooperation": database.query("SELECT COUNT(*) n FROM cooperation_requests", one=True)["n"],
        "cooperation_new": database.query("SELECT COUNT(*) n FROM cooperation_requests WHERE status='در انتظار بررسی'", one=True)["n"],
        "messages": database.query("SELECT COUNT(*) n FROM contact_messages", one=True)["n"],
        "messages_unread": database.query("SELECT COUNT(*) n FROM contact_messages WHERE is_read=0", one=True)["n"],
        "feedbacks": database.query("SELECT COUNT(*) n FROM feedbacks", one=True)["n"],
        "feedbacks_unread": database.query("SELECT COUNT(*) n FROM feedbacks WHERE is_read=0", one=True)["n"],
        "news": database.query("SELECT COUNT(*) n FROM news", one=True)["n"],
        "centers": database.query("SELECT COUNT(*) n FROM centers", one=True)["n"],
        "faqs": database.query("SELECT COUNT(*) n FROM faqs", one=True)["n"],
        "testimonials": database.query("SELECT COUNT(*) n FROM testimonials", one=True)["n"],
    }
    latest_bookings = database.query("SELECT * FROM bookings ORDER BY id DESC LIMIT 6")
    latest_messages = database.query("SELECT * FROM contact_messages ORDER BY id DESC LIMIT 6")
    return render_template("admin/dashboard.html", stats=stats,
                           latest_bookings=latest_bookings, latest_messages=latest_messages,
                           page_title="داشبورد مدیریت")


# ---------- مدیریت درخواست‌های نوبت ----------
@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    where, args = "WHERE 1=1", []
    if q:
        where += " AND (full_name LIKE ? OR phone LIKE ? OR tracking_code LIKE ?)"
        args += [f"%{q}%"] * 3
    if status:
        where += " AND status=?"
        args.append(status)
    rows = database.query(f"SELECT * FROM bookings {where} ORDER BY id DESC", args)
    return render_template("admin/bookings.html", rows=rows, q=q, status=status,
                           page_title="درخواست‌های نوبت")


@app.route("/admin/bookings/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_booking_detail(rid):
    row = database.query("SELECT * FROM bookings WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        database.execute(
            "UPDATE bookings SET status=?, admin_note=? WHERE id=?",
            (request.form.get("status", row["status"]),
             request.form.get("admin_note", ""), rid))
        flash("وضعیت درخواست به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_bookings"))
    return render_template("admin/booking_detail.html", row=row, page_title="جزئیات درخواست")


@app.route("/admin/bookings/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_booking_delete(rid):
    database.execute("DELETE FROM bookings WHERE id=?", (rid,))
    flash("درخواست حذف شد.", "success")
    return redirect(url_for("admin_bookings"))


# ---------- مدیریت درخواست‌های همکاری ----------
@app.route("/admin/cooperation")
@admin_required
def admin_cooperation():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    where, args = "WHERE 1=1", []
    if q:
        where += " AND (full_name LIKE ? OR phone LIKE ? OR tracking_code LIKE ?)"
        args += [f"%{q}%"] * 3
    if status:
        where += " AND status=?"
        args.append(status)
    rows = database.query(f"SELECT * FROM cooperation_requests {where} ORDER BY id DESC", args)
    return render_template("admin/cooperation.html", rows=rows, q=q, status=status,
                           page_title="درخواست‌های همکاری")


@app.route("/admin/cooperation/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_cooperation_detail(rid):
    row = database.query("SELECT * FROM cooperation_requests WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        database.execute(
            "UPDATE cooperation_requests SET status=?, admin_note=? WHERE id=?",
            (request.form.get("status", row["status"]),
             request.form.get("admin_note", ""), rid))
        flash("وضعیت درخواست به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_cooperation"))
    return render_template("admin/cooperation_detail.html", row=row, page_title="جزئیات درخواست همکاری")


@app.route("/admin/cooperation/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_cooperation_delete(rid):
    database.execute("DELETE FROM cooperation_requests WHERE id=?", (rid,))
    flash("درخواست حذف شد.", "success")
    return redirect(url_for("admin_cooperation"))


# ---------- مدیریت پیام‌ها ----------
@app.route("/admin/messages")
@admin_required
def admin_messages():
    rows = database.query("SELECT * FROM contact_messages ORDER BY id DESC")
    return render_template("admin/messages.html", rows=rows, page_title="پیام‌های تماس")


@app.route("/admin/messages/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_message_detail(rid):
    row = database.query("SELECT * FROM contact_messages WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    database.execute("UPDATE contact_messages SET is_read=1 WHERE id=?", (rid,))
    if request.method == "POST":
        database.execute("DELETE FROM contact_messages WHERE id=?", (rid,))
        flash("پیام حذف شد.", "success")
        return redirect(url_for("admin_messages"))
    return render_template("admin/message_detail.html", row=row, page_title="جزئیات پیام")


@app.route("/admin/feedbacks")
@admin_required
def admin_feedbacks():
    rows = database.query("SELECT * FROM feedbacks ORDER BY id DESC")
    return render_template("admin/feedbacks.html", rows=rows, page_title="پیشنهادها و انتقادها")


@app.route("/admin/feedbacks/<int:rid>/toggle", methods=["POST"])
@admin_required
@admin_csrf
def admin_feedback_toggle(rid):
    database.execute("UPDATE feedbacks SET is_read = 1 - is_read WHERE id=?", (rid,))
    return redirect(url_for("admin_feedbacks"))


@app.route("/admin/feedbacks/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_feedback_delete(rid):
    database.execute("DELETE FROM feedbacks WHERE id=?", (rid,))
    flash("مورد حذف شد.", "success")
    return redirect(url_for("admin_feedbacks"))


# ---------- مدیریت اخبار ----------
@app.route("/admin/news")
@admin_required
def admin_news():
    rows = database.query("SELECT * FROM news ORDER BY id DESC")
    return render_template("admin/news.html", rows=rows, page_title="مدیریت اخبار")


def _slugify(title, existing_id=None):
    import re as _re
    base = _re.sub(r"\s+", "-", title.strip())[:60] or "news"
    slug = base
    i = 2
    while True:
        row = database.query("SELECT id FROM news WHERE slug=?", (slug,), one=True)
        if not row or (existing_id and row["id"] == existing_id):
            break
        slug = f"{base}-{i}"
        i += 1
    return slug


@app.route("/admin/news/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_news_new():
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("عنوان الزامی است.", "error")
            return redirect(request.url)
        slug = f.get("slug", "").strip() or _slugify(title)
        database.execute(
            """INSERT INTO news (title, slug, summary, content, category, published)
            VALUES (?,?,?,?,?,?)""",
            (title, slug, f.get("summary", "").strip(), f.get("content", "").strip(),
             f.get("category", "اخبار"), 1 if f.get("published") else 0))
        flash("خبر جدید ایجاد شد.", "success")
        return redirect(url_for("admin_news"))
    return render_template("admin/news_form.html", item=None, page_title="خبر جدید")


@app.route("/admin/news/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_news_edit(rid):
    row = database.query("SELECT * FROM news WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("عنوان الزامی است.", "error")
            return redirect(request.url)
        slug = f.get("slug", "").strip() or _slugify(title, rid)
        database.execute(
            """UPDATE news SET title=?, slug=?, summary=?, content=?, category=?, published=?
            WHERE id=?""",
            (title, slug, f.get("summary", "").strip(), f.get("content", "").strip(),
             f.get("category", "اخبار"), 1 if f.get("published") else 0, rid))
        flash("خبر به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_news"))
    return render_template("admin/news_form.html", item=row, page_title="ویرایش خبر")


@app.route("/admin/news/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_news_delete(rid):
    database.execute("DELETE FROM news WHERE id=?", (rid,))
    flash("خبر حذف شد.", "success")
    return redirect(url_for("admin_news"))


# ---------- مدیریت مراکز استانی ----------
@app.route("/admin/centers")
@admin_required
def admin_centers():
    rows = database.query("SELECT * FROM centers ORDER BY is_soon, sort_order")
    return render_template("admin/centers.html", rows=rows, page_title="مدیریت مراکز استانی")


@app.route("/admin/centers/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_centers_new():
    if request.method == "POST":
        f = request.form
        if not f.get("province", "").strip():
            flash("نام استان الزامی است.", "error")
            return redirect(request.url)
        database.execute(
            """INSERT INTO centers (province, clinic_name, address, postal_code, clinic_phone,
            manager_name, manager_phone, exec_name, exec_phone, work_hours, map_url, is_soon, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f.get("province", "").strip(), f.get("clinic_name", "").strip(),
             f.get("address", "").strip(), f.get("postal_code", "").strip(),
             f.get("clinic_phone", "").strip(), f.get("manager_name", "").strip(),
             f.get("manager_phone", "").strip(), f.get("exec_name", "").strip(),
             f.get("exec_phone", "").strip(), f.get("work_hours", "").strip(),
             f.get("map_url", "").strip(), 1 if f.get("is_soon") else 0,
             f.get("sort_order", 0, type=int)))
        flash("مرکز جدید اضافه شد.", "success")
        return redirect(url_for("admin_centers"))
    return render_template("admin/center_form.html", item=None, page_title="مرکز جدید")


@app.route("/admin/centers/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_centers_edit(rid):
    row = database.query("SELECT * FROM centers WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        f = request.form
        database.execute(
            """UPDATE centers SET province=?, clinic_name=?, address=?, postal_code=?,
            clinic_phone=?, manager_name=?, manager_phone=?, exec_name=?, exec_phone=?,
            work_hours=?, map_url=?, is_soon=?, sort_order=? WHERE id=?""",
            (f.get("province", "").strip(), f.get("clinic_name", "").strip(),
             f.get("address", "").strip(), f.get("postal_code", "").strip(),
             f.get("clinic_phone", "").strip(), f.get("manager_name", "").strip(),
             f.get("manager_phone", "").strip(), f.get("exec_name", "").strip(),
             f.get("exec_phone", "").strip(), f.get("work_hours", "").strip(),
             f.get("map_url", "").strip(), 1 if f.get("is_soon") else 0,
             f.get("sort_order", 0, type=int), rid))
        flash("مرکز به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_centers"))
    return render_template("admin/center_form.html", item=row, page_title="ویرایش مرکز")


@app.route("/admin/centers/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_centers_delete(rid):
    database.execute("DELETE FROM centers WHERE id=?", (rid,))
    flash("مرکز حذف شد.", "success")
    return redirect(url_for("admin_centers"))


# ---------- مدیریت سوالات متداول ----------
@app.route("/admin/faqs")
@admin_required
def admin_faqs():
    rows = database.query("SELECT * FROM faqs ORDER BY sort_order")
    categories = [r["category"] for r in database.query("SELECT DISTINCT category FROM faqs")]
    return render_template("admin/faqs.html", rows=rows, categories=categories,
                           page_title="سوالات متداول")


@app.route("/admin/faqs/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_faqs_new():
    q = request.form.get("question", "").strip()
    a = request.form.get("answer", "").strip()
    if q and a:
        mx = database.query("SELECT MAX(sort_order) m FROM faqs", one=True)["m"] or 0
        database.execute(
            "INSERT INTO faqs (category, question, answer, sort_order) VALUES (?,?,?,?)",
            (request.form.get("category", "عمومی").strip() or "عمومی", q, a, mx + 1))
        flash("سوال جدید اضافه شد.", "success")
    return redirect(url_for("admin_faqs"))


@app.route("/admin/faqs/<int:rid>/edit", methods=["POST"])
@admin_required
@admin_csrf
def admin_faqs_edit(rid):
    database.execute(
        "UPDATE faqs SET category=?, question=?, answer=? WHERE id=?",
        (request.form.get("category", "عمومی").strip(), request.form.get("question", "").strip(),
         request.form.get("answer", "").strip(), rid))
    flash("سوال به‌روزرسانی شد.", "success")
    return redirect(url_for("admin_faqs"))


@app.route("/admin/faqs/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_faqs_delete(rid):
    database.execute("DELETE FROM faqs WHERE id=?", (rid,))
    flash("سوال حذف شد.", "success")
    return redirect(url_for("admin_faqs"))


# ---------- مدیریت نظرات مراجعین ----------
@app.route("/admin/testimonials")
@admin_required
def admin_testimonials():
    rows = database.query("SELECT * FROM testimonials ORDER BY sort_order")
    return render_template("admin/testimonials.html", rows=rows, page_title="نظرات مراجعین")


@app.route("/admin/testimonials/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_testimonials_new():
    name = request.form.get("name", "").strip()
    text = request.form.get("text", "").strip()
    if name and text:
        mx = database.query("SELECT MAX(sort_order) m FROM testimonials", one=True)["m"] or 0
        database.execute(
            "INSERT INTO testimonials (name, category, text, sort_order) VALUES (?,?,?,?)",
            (name, request.form.get("category", "").strip(), text, mx + 1))
        flash("نظر جدید اضافه شد.", "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/<int:rid>/edit", methods=["POST"])
@admin_required
@admin_csrf
def admin_testimonials_edit(rid):
    database.execute(
        "UPDATE testimonials SET name=?, category=?, text=? WHERE id=?",
        (request.form.get("name", "").strip(), request.form.get("category", "").strip(),
         request.form.get("text", "").strip(), rid))
    flash("نظر به‌روزرسانی شد.", "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_testimonials_delete(rid):
    database.execute("DELETE FROM testimonials WHERE id=?", (rid,))
    flash("نظر حذف شد.", "success")
    return redirect(url_for("admin_testimonials"))


# ---------- مدیریت خدمات (نمایش/ترتیب) ----------
@app.route("/admin/services", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_services():
    if request.method == "POST":
        for sid, in database.query("SELECT id FROM services"):
            database.execute(
                "UPDATE services SET is_visible=?, menu_order=? WHERE id=?",
                (1 if request.form.get(f"visible_{sid}") else 0,
                 request.form.get(f"order_{sid}", 0, type=int), sid))
        flash("خدمات به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_services"))
    rows = database.query("SELECT * FROM services ORDER BY menu_order")
    return render_template("admin/services.html", rows=rows, page_title="مدیریت خدمات")


# ---------- تنظیمات ----------
@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_settings():
    if request.method == "POST":
        allowed = set(get_settings().keys())
        for k in allowed:
            if k in request.form:
                database.execute("UPDATE settings SET value=? WHERE key=?",
                                 (request.form.get(k, "").strip(), k))
        flash("تنظیمات ذخیره شد.", "success")
        g.pop("settings", None)
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html", s=get_settings(), page_title="تنظیمات سایت")


@app.route("/admin/password", methods=["POST"])
@admin_required
@admin_csrf
def admin_password():
    cur = database.query("SELECT * FROM admin_users WHERE id=?", (session["admin_id"],), one=True)
    if cur and check_password_hash(cur["password_hash"], request.form.get("old_password", "")):
        new1 = request.form.get("new_password", "")
        if len(new1) >= 6 and new1 == request.form.get("new_password2", ""):
            database.execute("UPDATE admin_users SET password_hash=? WHERE id=?",
                             (generate_password_hash(new1), cur["id"]))
            flash("گذرواژه با موفقیت تغییر کرد.", "success")
            return redirect(url_for("admin_settings"))
        flash("گذرواژه جدید باید حداقل ۶ کاراکتر باشد و با تکرار آن مطابقت داشته باشد.", "error")
    else:
        flash("گذرواژه فعلی نادرست است.", "error")
    return redirect(url_for("admin_settings"))


# ==================================================================
# خطاها و API
# ==================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", page_title="صفحه یافت نشد"), 404


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "rosecenter-flask"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
