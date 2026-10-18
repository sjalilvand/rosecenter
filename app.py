# -*- coding: utf-8 -*-
"""
وب‌سایت مرکز خدمات روانشناسی و مشاوره رز
بازنویسی کامل با Flask + SQLite
"""
import os
import secrets
import string
import math
import re
import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, g, jsonify, send_from_directory,
)
from werkzeug.security import check_password_hash, generate_password_hash

import database
import jalali as jdate
from config import THERAPY_TYPES, REQUEST_STATUSES

app = Flask(__name__)
app.config.from_object("config")

# مدت زنده‌ماندن سشن لاگین (۳۰ روز) و رفرش هر درخواست
from datetime import timedelta
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# فاصله‌ای که کاربر «آنلاین» در نظر گرفته می‌شود (ثانیه)
ONLINE_WINDOW = 300

UPLOAD_FOLDER = os.path.join(app.config.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__))), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

database.init_db(app)

# اتصال خودکار به دیتابیس در هر درخواست
def _ensure_db():
    database.get_db()


def _touch_session():
    """ردیابی سشن‌ها: بروزرسانی آخرین حضور + ابطال سشن‌های خروج‌کرده توسط ادمین"""
    sid = session.get("sid")
    if not sid:
        return
    row = database.query(
        "SELECT is_active FROM user_sessions WHERE sid=?", (sid,), one=True)
    if not row or not row["is_active"]:
        # ادمین این سشن را از پنل بسته است
        session.clear()
        return
    if (session.get("uid") or session.get("admin_id")):
        database.execute(
            "UPDATE user_sessions SET last_seen_at=datetime('now','localtime') WHERE sid=? AND is_active=1",
            (sid,))


app.before_request(_ensure_db)
app.before_request(_touch_session)
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


def _jdatetime_filter(value, with_time=False):
    """فیلتر Jinja: تبدیل تاریخ میلادی رشته‌ای به شمسی خوانا"""
    if not value:
        return ""
    s = str(value)
    try:
        d = datetime.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            d = datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return s
    jy, jm, jd = jdate.gregorian_to_jalali(d.year, d.month, d.day)
    txt = jdate.format_jalali(jy, jm, jd)
    if with_time and " " in s:
        txt += " — " + s[11:16]
    return txt


app.jinja_env.filters["jdate"] = _jdatetime_filter


def valid_csrf():
    tok = request.form.get("_csrf", "")
    return tok and tok == session.get("_csrf")


# ------------------------------------------------------------------
# مدیریت سشن لاگین (ثبت / اتمام / ردیابی)
# ------------------------------------------------------------------
def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or ""


def register_session(kind, display_name, user_id=None):
    """ثبت سشن جدید پس از لاگین (کاربر عادی یا ادمین)"""
    sid = secrets.token_hex(16)
    session["sid"] = sid
    session.permanent = True
    ua = request.headers.get("User-Agent", "")[:300]
    database.execute(
        """INSERT INTO user_sessions (sid, kind, user_id, display_name, ip, user_agent)
           VALUES (?,?,?,?,?,?)""",
        (sid, kind, user_id, display_name, _client_ip(), ua))
    return sid


def end_session():
    """پایان سشن جاری و ثبت زمان خروج"""
    sid = session.pop("sid", None)
    if sid:
        database.execute(
            """UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime')
               WHERE sid=? AND is_active=1""", (sid,))


def current_user():
    """اطلاعات کاربر لاگین‌شده فعلی (یا None)"""
    if "uid" not in session or "cur_user" not in g:
        if "uid" not in session:
            return None
        g.cur_user = database.query(
            "SELECT * FROM users WHERE id=? AND is_active=1", (session["uid"],), one=True)
        if not g.cur_user:
            session.clear()
            return None
    return g.cur_user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


# ------------------------------------------------------------------
# کپچا (تصویر SVG با عبارت ریاضی)
# ------------------------------------------------------------------
def generate_captcha():
    """ساخت عبارت ریاضی کپچا و ذخیره پاسخ در سشن"""
    a = secrets.randbelow(9) + 1   # ۱ تا ۹
    b = secrets.randbelow(9) + 1   # ۱ تا ۹
    session["captcha_answer"] = str(a + b)
    return a, b


def check_captcha():
    """بررسی پاسخ کپچا و تولید عبارت جدید برای بار بعد"""
    ans = jdate.en_digits(request.form.get("captcha", "")).strip()
    ok = ans and session.pop("captcha_answer", None) == ans
    generate_captcha()  # هر بار عبارت جدید
    return ok


@app.route("/captcha.png")
def captcha_image():
    """تصویر کپچا به‌صورت SVG (بدون نیاز به کتابخانه خارجی)"""
    a, b = generate_captcha()
    exp = f"{jdate.fa_digits(a)} + {jdate.fa_digits(b)}"

    import random
    rnd = random.Random(secrets.token_hex(8))

    glyphs = []
    x = 26
    for ch in exp:
        rot = rnd.randint(-22, 22)
        dy = rnd.randint(-4, 4)
        color = rnd.choice(["#4f46e5", "#0891b2", "#be185d", "#b45309", "#047857"])
        glyphs.append(
            f'<text x="{x}" y="{34 + dy}" transform="rotate({rot} {x} 34)" '
            f'fill="{color}" font-size="{rnd.randint(24, 30)}" '
            f'font-family="Vazirmatn, Tahoma, sans-serif" font-weight="bold">{ch}</text>'
        )
        x += 24 if ch != " " else 14

    lines = ""
    for _ in range(4):
        x1, y1 = rnd.randint(0, 140), rnd.randint(0, 50)
        x2, y2 = rnd.randint(0, 140), rnd.randint(0, 50)
        lines += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#{secrets.token_hex(3)}" stroke-width="1" opacity="0.45"/>'

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="170" height="54" viewBox="0 0 170 54">'
           f'<rect width="170" height="54" rx="10" fill="#f1f5f9"/>{lines}{"".join(glyphs)}</svg>')
    return app.response_class(svg, mimetype="image/svg+xml",
                              headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


def get_settings():
    """خواندن تنظیمات سایت (کش در هر درخواست)"""
    if "settings" not in g:
        rows = database.query("SELECT key, value FROM settings")
        g.settings = {r["key"]: r["value"] for r in rows}
    return g.settings


def get_visible_services():
    return database.query("SELECT * FROM services WHERE is_visible=1 ORDER BY menu_order")


def get_nav_course_categories():
    """دسته‌بندی‌های دوره برای منوی مگا"""
    return database.query(
        "SELECT * FROM course_categories WHERE is_visible=1 ORDER BY sort_order")


@app.context_processor
def inject_globals():
    u = current_user()
    return {
        "settings": get_settings(),
        "nav_services": get_visible_services(),
        "nav_course_categories": get_nav_course_categories(),
        "REQUEST_STATUSES": REQUEST_STATUSES,
        "today_jalali_fa": jdate.today_jalali_fa(),
        "cur_user": u,
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
    # بلوک‌های دینامیک صفحه اصلی (مدیریت از پنل ادمین)
    blocks = _load_home_blocks()
    # بخش‌های دوره‌ها به سبک LMS
    courses_registration = _course_card_rows(
        "WHERE c.is_open=1 AND c.status='registration'", (), 8)
    courses_popular = _course_card_rows(
        "WHERE c.is_open=1", (), 4, order_by="c.students DESC, c.rating DESC")
    courses_free = _course_card_rows(
        "WHERE c.is_open=1 AND c.is_free=1", (), 4)
    course_cats = get_nav_course_categories()
    forum_teaser = database.query(
        """SELECT t.*, fc.title AS cat_title, fc.slug AS cat_slug, fc.icon AS cat_icon,
           (SELECT COUNT(*) FROM forum_posts p WHERE p.topic_id=t.id AND p.is_visible=1) AS replies
           FROM forum_topics t JOIN forum_categories fc ON fc.id=t.category_id
           WHERE t.is_visible=1 ORDER BY t.last_activity_at DESC LIMIT 4""")
    forum_cats = _forum_categories_with_counts()
    latest_news = database.query(
        "SELECT * FROM news WHERE published=1 ORDER BY published_at DESC, id DESC LIMIT 3")
    return render_template("home.html", services=services, testimonials=testimonials,
                           faqs=faqs, centers=centers, blocks=blocks,
                           courses_registration=courses_registration,
                           courses_popular=courses_popular, courses_free=courses_free,
                           course_cats=course_cats, forum_teaser=forum_teaser,
                           forum_cats=forum_cats, latest_news=latest_news,
                           status_labels=COURSE_STATUS_LABELS,
                           page_title="خانه")


HOME_BLOCK_KINDS = {
    "custom":  "آیتم سفارشی",
    "form":    "فرم / دسترسی سریع",
    "article": "مقاله / خبر",
    "course":  "دوره آموزشی",
    "service": "خدمت",
}


def _load_home_blocks():
    """بارگذاری بلوک‌های فعال صفحه اصلی و اتصال به مقاله/دوره مرتبط"""
    rows = database.query("SELECT * FROM home_blocks WHERE is_visible=1 ORDER BY sort_order, id")
    out = []
    for r in rows:
        b = dict(r)
        b["kind_label"] = HOME_BLOCK_KINDS.get(r["kind"], r["kind"])
        if r["kind"] == "article" and r["ref_id"]:
            art = database.query(
                "SELECT slug, title, summary FROM news WHERE id=? AND published=1", (r["ref_id"],), one=True)
            if art:
                b["link"] = url_for("news_detail", slug=art["slug"])
                b["title"] = b["title"] or art["title"]
                b["subtitle"] = b["subtitle"] or art["summary"]
        elif r["kind"] == "course" and r["ref_id"]:
            c = database.query(
                "SELECT slug, title, summary, teacher, price FROM courses WHERE id=? AND is_open=1",
                (r["ref_id"],), one=True)
            if c:
                b["link"] = url_for("course_detail", slug=c["slug"])
                b["title"] = b["title"] or c["title"]
                b["subtitle"] = b["subtitle"] or c["summary"]
        elif r["kind"] == "form":
            b.setdefault("link", "")
        out.append(b)
    return out


# فرم‌های قابل انتخاب برای بلوک «فرم / دسترسی سریع»
QUICK_FORMS = [
    ("/consultation/", "درخواست مشاوره", "📝"),
    ("/cooperation/", "فراخوان همکاری", "🤝"),
    ("/tracking/", "پیگیری درخواست", "🔎"),
    ("/feedback/", "پیشنهاد و انتقاد", "💬"),
    ("/contact/", "تماس با ما", "✉️"),
    ("/jalali/", "تبدیل تاریخ شمسی", "📅"),
]


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


# ------------------------------------------------------------------
# اعتبارسنجی کد ملی و موبایل (مطابق فرم فراخوان همکاری)
# ------------------------------------------------------------------
def validate_national_code(code):
    """اعتبارسنجی کد ملی ۱۰ رقمی ایرانی"""
    code = jdate.en_digits(str(code)).strip()
    if not code or not code.isdigit() or len(code) != 10:
        return False
    if code == code[0] * 10:
        return False
    check = int(code[9])
    total = sum(int(code[i]) * (10 - i) for i in range(9))
    r = total % 11
    return (r < 2 and check == r) or (r >= 2 and check == 11 - r)


def validate_mobile(num):
    num = jdate.en_digits(str(num)).strip()
    return len(num) == 11 and num.startswith("09") and num.isdigit()


def validate_phone11(num):
    num = jdate.en_digits(str(num)).strip()
    return len(num) == 11 and num.startswith("0") and num.isdigit()


# فایل‌های مجاز آپلود فراخوان همکاری (حداکثر ۵۰ کیلوبایت)
HR_FILES = {
    "nationalCardFile": "کارت_ملی",
    "militaryFile": "پایان_خدمت",
    "educationFile": "مدرک_تحصیلی",
    "licenseFile": "پروانه",
    "centerLicenseFile": "پروانه_مرکز",
    "centerPermitFile": "مجوز_مرکز",
    "propertyFile": "مدارک_ملک",
}
HR_MAX_KB = 50
HR_ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif", "pdf"}


def _save_hr_file(file_storage, tracking_code, label):
    """ذخیره فایل آپلودی فراخوان با بررسی حجم و پسوند — خروجی: نام فایل یا رشته خالی"""
    if not file_storage or not file_storage.filename:
        return ""
    filename = os.path.basename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in HR_ALLOWED_EXT:
        raise ValueError(f"پسوند فایل {label} مجاز نیست (فقط تصویر یا PDF)")
    data = file_storage.read()
    if len(data) > HR_MAX_KB * 1024:
        raise ValueError(f"حجم فایل {label} نباید بیشتر از {HR_MAX_KB} کیلوبایت باشد")
    safe_name = f"{tracking_code.replace('-', '_')}_{label}.{ext}"
    with open(os.path.join(app.config["UPLOAD_FOLDER"], safe_name), "wb") as fh:
        fh.write(data)
    return safe_name


@app.route("/cooperation/", methods=["GET", "POST"])
@app.route("/فراخوان-همکاری/", methods=["GET", "POST"])
def cooperation():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        first = f.get("firstName", "").strip()
        last = f.get("lastName", "").strip()
        ncode = jdate.en_digits(f.get("nationalCode", "")).strip()
        mobile = jdate.en_digits(f.get("mobile", "")).strip()

        if not first or not last:
            return jsonify({"result": "error", "message": "نام و نام خانوادگی الزامی است"}), 400
        if not validate_national_code(ncode):
            return jsonify({"result": "error", "message": "کد ملی نامعتبر است"}), 400
        if not validate_mobile(mobile):
            return jsonify({"result": "error", "message": "شماره همراه نامعتبر است (۰۹xxxxxxxxx)"}), 400
        if not check_captcha():
            return jsonify({"result": "error", "message": "پاسخ کپچا نادرست است؛ لطفاً دوباره تلاش کنید"}), 400

        code = gen_tracking_code("HR")
        try:
            saved = {}
            for field, label in HR_FILES.items():
                saved[field] = _save_hr_file(request.files.get(field), code, label)
        except ValueError as err:
            return jsonify({"result": "error", "message": str(err)}), 400

        def _num(key):
            try:
                return int(jdate.en_digits(f.get(key, "0")) or 0)
            except ValueError:
                return 0

        database.execute(
            """INSERT INTO hr_calls
            (tracking_code, first_name, last_name, national_code, birth_date,
             gender, military_status, military_file,
             education_level, education_file,
             license_status, license_file, center_license_file, license_desc, center_permit_file,
             ownership_status, property_file,
             province, county, center_phone, postal_code, full_address,
             individual_rooms, group_rooms, child_rooms, counselors_count,
             waiting_area, design_acceptance, accessibility, mobile, national_card_file, user_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, first, last, ncode, jdate.en_digits(f.get("birthDate", "")).strip(),
             f.get("gender", "").strip(), f.get("militaryStatus", "").strip(), saved["militaryFile"],
             f.get("educationLevel", "").strip(), saved["educationFile"],
             f.get("licenseStatus", "").strip(), saved["licenseFile"], saved["centerLicenseFile"],
             f.get("licenseDesc", "").strip(), saved["centerPermitFile"],
             f.get("ownershipStatus", "").strip(), saved["propertyFile"],
             f.get("province", "").strip(), f.get("county", "").strip(),
             jdate.en_digits(f.get("centerPhone", "")).strip(),
             jdate.en_digits(f.get("postalCode", "")).strip(),
             f.get("fullAddress", "").strip(),
             _num("individualRooms"), _num("groupRooms"), _num("childRooms"), _num("counselorsCount"),
             f.get("waitingArea", "").strip(), f.get("designAcceptance", "").strip(),
             f.get("accessibility", "").strip(), mobile, saved["nationalCardFile"],
             session.get("uid")),
        )
        return jsonify({"result": "success", "message": "اطلاعات شما با موفقیت ثبت شد ✅",
                        "tracking_code": code})

    generate_captcha()  # عبارت کپچا اولیه
    provinces = database.query("SELECT province FROM centers ORDER BY sort_order")
    return render_template("cooperation.html", provinces=provinces, page_title="فراخوان همکاری")


@app.route("/academy/")
def academy():
    rows = database.query("SELECT * FROM courses WHERE is_open=1 ORDER BY sort_order, id DESC")
    regs_count = database.query(
        "SELECT course_id, COUNT(*) AS n FROM course_registrations GROUP BY course_id")
    counts = {r["course_id"]: r["n"] for r in regs_count}
    return render_template("academy.html", courses=rows, counts=counts, page_title="آکادمی رز — دوره‌های آموزشی")


# ==================================================================
# دوره‌های آموزشی — سبک LMS مدرسه‌ای (مانند روان‌بُنه)
# ==================================================================
COURSE_STATUS_LABELS = {
    "registration": "در حال ثبت‌نام",
    "running": "در حال برگزاری",
    "ended": "برگزار شده",
}


def _course_card_rows(where_sql, args, limit=None, order_by="c.sort_order, c.id DESC"):
    """کوئری دوره‌ها با دسته و تعداد ثبت‌نام برای کارت‌های LMS"""
    sql = f"""SELECT c.*, cc.title AS cat_title, cc.slug AS cat_slug, cc.icon AS cat_icon,
              (SELECT COUNT(*) FROM course_registrations r WHERE r.course_id=c.id) AS regs
              FROM courses c LEFT JOIN course_categories cc ON cc.id = c.category_id
              {where_sql} ORDER BY {order_by}"""
    if limit:
        sql += f" LIMIT {int(limit)}"
    return database.query(sql, args)


@app.route("/courses/")
def courses():
    tab = request.args.get("tab", "all").strip()
    cat = request.args.get("cat", "").strip()
    q = request.args.get("q", "").strip()

    base_where, base_args = "WHERE c.is_open=1", []
    join = ""
    if cat:
        join = "JOIN course_categories cc ON cc.id = c.category_id AND cc.slug=?"
        base_args.append(cat)
    if q:
        base_where += " AND (c.title LIKE ? OR c.summary LIKE ? OR c.teacher LIKE ?)"
        base_args += [f"%{q}%"] * 3

    # تب‌ها و شمارنده‌ها
    tabs = [
        ("all", "همه دوره‌ها"),
        ("registration", "در حال ثبت‌نام"),
        ("running", "در حال برگزاری"),
        ("popular", "پرمخاطب‌ترین"),
        ("free", "رایگان"),
        ("special", "دوره‌های ویژه"),
    ]
    tab_counts = {}
    for key, _label in tabs:
        w, a = base_where, list(base_args)
        if key == "registration":
            w += " AND c.status='registration'"
        elif key == "running":
            w += " AND c.status='running'"
        elif key == "popular":
            w += " AND c.students >= 100"
        elif key == "free":
            w += " AND c.is_free=1"
        elif key == "special":
            w += " AND c.is_special=1"
        row = database.query(
            f"SELECT COUNT(*) n FROM courses c {join} {w}", a, one=True)
        tab_counts[key] = row["n"]

    # کوئری اصلی با فیلتر تب
    where = base_where
    if tab == "registration":
        where += " AND c.status='registration'"
    elif tab == "running":
        where += " AND c.status='running'"
    elif tab == "popular":
        where += " AND c.students >= 100"
        # پرمخاطب‌ترین: مرتب‌سازی بر اساس تعداد دانشجو
        rows = _course_card_rows(where, base_args)
        rows = sorted(rows, key=lambda r: r["students"], reverse=True)
        cats = get_nav_course_categories()
        return render_template("courses.html", courses=rows, tabs=tabs, tab=tab,
                               tab_counts=tab_counts, cats=cats, cat=cat, q=q,
                               status_labels=COURSE_STATUS_LABELS,
                               page_title="دوره‌های آموزشی")
    elif tab == "free":
        where += " AND c.is_free=1"
    elif tab == "special":
        where += " AND c.is_special=1"

    rows = _course_card_rows(where, base_args)
    cats = get_nav_course_categories()
    return render_template("courses.html", courses=rows, tabs=tabs, tab=tab,
                           tab_counts=tab_counts, cats=cats, cat=cat, q=q,
                           status_labels=COURSE_STATUS_LABELS,
                           page_title="دوره‌های آموزشی")


@app.route("/academy/course/<slug>/")
def course_detail(slug):
    course = database.query(
        """SELECT c.*, cc.title AS cat_title, cc.slug AS cat_slug, cc.icon AS cat_icon,
           (SELECT COUNT(*) FROM course_registrations r WHERE r.course_id=c.id) AS regs
           FROM courses c LEFT JOIN course_categories cc ON cc.id = c.category_id
           WHERE c.slug=? AND c.is_open=1""", (slug,), one=True)
    if not course:
        abort(404)
    others = database.query(
        """SELECT c.*, cc.title AS cat_title FROM courses c
           LEFT JOIN course_categories cc ON cc.id = c.category_id
           WHERE c.is_open=1 AND c.id!=? ORDER BY c.sort_order LIMIT 3""", (course["id"],))
    return render_template("course_detail.html", course=course,
                           status_labels=COURSE_STATUS_LABELS,
                           others=others, page_title=course["title"])


@app.route("/academy/register/<int:course_id>/", methods=["GET", "POST"])
def course_register(course_id):
    course = database.query("SELECT * FROM courses WHERE id=? AND is_open=1", (course_id,), one=True)
    if not course:
        abort(404)

    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        first = f.get("first_name", "").strip()
        last = f.get("last_name", "").strip()
        ncode = jdate.en_digits(f.get("national_code", "")).strip()
        mobile = jdate.en_digits(f.get("mobile", "")).strip()

        if not first or not last:
            flash("نام و نام خانوادگی الزامی است.", "error")
        elif not validate_national_code(ncode):
            flash("کد ملی وارد شده معتبر نیست.", "error")
        elif not validate_mobile(mobile):
            flash("شماره همراه باید ۱۱ رقم و با ۰۹ شروع شود.", "error")
        elif not check_captcha():
            flash("پاسخ کپچا نادرست است؛ لطفاً دوباره تلاش کنید.", "error")
        else:
            code = gen_tracking_code("CRS")
            database.execute(
                """INSERT INTO course_registrations
                (tracking_code, course_id, first_name, last_name, national_code, mobile,
                 phone, email, education, city, note, user_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, course_id, first, last, ncode, mobile,
                 jdate.en_digits(f.get("phone", "")).strip(), f.get("email", "").strip(),
                 f.get("education", "").strip(), f.get("city", "").strip(),
                 f.get("note", "").strip(), session.get("uid")),
            )
            session["last_code"] = code
            return render_template("course_register.html", course=course, success_code=code,
                                   page_title=f"ثبت‌نام — {course['title']}")
        return redirect(url_for("course_register", course_id=course_id))

    generate_captcha()
    registered = database.query(
        "SELECT COUNT(*) n FROM course_registrations WHERE course_id=?", (course_id,), one=True)["n"]
    full = course["capacity"] and registered >= course["capacity"]
    return render_template("course_register.html", course=course, registered=registered,
                           full=full, page_title=f"ثبت‌نام — {course['title']}")


# ------------------------------------------------------------------
# تبدیل تاریخ شمسی ↔ میلادی
# ------------------------------------------------------------------
@app.route("/jalali/")
def jalali_converter():
    today = jdate.today_jalali()
    return render_template("jalali.html",
                           today_fa=jdate.today_jalali_fa(),
                           today_j=today,
                           months=jdate.JALALI_MONTHS,
                           page_title="تبدیل تاریخ شمسی و میلادی")


@app.route("/api/jalali/convert")
def api_jalali_convert():
    """API تبدیل تاریخ — ?mode=g2j&y=2026&m=10&d=18 یا ?mode=j2g&y=1405&m=7&d=26"""
    mode = request.args.get("mode", "g2j")
    try:
        y = int(jdate.en_digits(request.args.get("y", "")))
        m = int(jdate.en_digits(request.args.get("m", "")))
        d = int(jdate.en_digits(request.args.get("d", "")))
        if mode == "j2g":
            gy, gm, gd = jdate.jalali_to_gregorian(y, m, d)
            jy, jm, jd = y, m, d
            if not (1 <= jm <= 12 and 1 <= jd <= jdate.jalali_month_days(jy, jm)):
                raise ValueError("تاریخ شمسی وارد شده معتبر نیست")
        else:
            import datetime
            gy, gm, gd = y, m, d
            datetime.date(gy, gm, gd)  # بررسی اعتبار تاریخ میلادی
            jy, jm, jd = jdate.gregorian_to_jalali(gy, gm, gd)
        return jsonify({
            "result": "ok",
            "gregorian": {"y": gy, "m": gm, "d": gd, "text": f"{gy:04d}/{gm:02d}/{gd:02d}"},
            "jalali": {"y": jy, "m": jm, "d": jd,
                       "text": f"{jdate.fa_digits(jy)}/{jdate.fa_digits(f'{jm:02d}')}/{jdate.fa_digits(f'{jd:02d}')}",
                       "month_name": jdate.JALALI_MONTHS[jm - 1],
                       "weekday": jdate.WEEK_DAYS_FA[jdate.jalali_weekday(jy, jm, jd)]},
        })
    except (ValueError, OverflowError) as err:
        return jsonify({"result": "error", "message": str(err) or "تاریخ وارد شده معتبر نیست"}), 400


@app.route("/api/jalali/today")
def api_jalali_today():
    jy, jm, jd = jdate.today_jalali()
    gy, gm, gd = jdate.tehran_today()
    return jsonify({
        "result": "ok",
        "gregorian": {"y": gy, "m": gm, "d": gd, "text": f"{gy:04d}/{gm:02d}/{gd:02d}"},
        "jalali": {"y": jy, "m": jm, "d": jd, "text": jdate.format_jalali(jy, jm, jd)},
        "today_fa": jdate.today_jalali_fa(),
    })


# ==================================================================
# انجمن‌های تخصصی (Forum)
# ==================================================================
def _forum_categories_with_counts():
    return database.query(
        """SELECT fc.*,
             (SELECT COUNT(*) FROM forum_topics t WHERE t.category_id=fc.id AND t.is_visible=1) AS topics_count,
             (SELECT COUNT(*) FROM forum_posts p JOIN forum_topics t2 ON t2.id=p.topic_id
               WHERE t2.category_id=fc.id AND p.is_visible=1 AND t2.is_visible=1) AS posts_count
           FROM forum_categories fc WHERE fc.is_visible=1 ORDER BY fc.sort_order, fc.id""")


def _forum_last_activity(category_id):
    row = database.query(
        """SELECT MAX(x.at) at FROM (
             SELECT last_activity_at at FROM forum_topics WHERE category_id=? AND is_visible=1
             UNION ALL
             SELECT p.created_at at FROM forum_posts p JOIN forum_topics t ON t.id=p.topic_id
             WHERE t.category_id=? AND p.is_visible=1 AND t.is_visible=1) x""", (category_id, category_id), one=True)
    return row["at"] if row and row["at"] else ""


@app.route("/forum/")
def forum_index():
    cats = _forum_categories_with_counts()
    for c in cats:
        c["last_at"] = _forum_last_activity(c["id"])
    # آخرین تاپیک‌های فعال برای نمایش در صفحه اول انجمن
    latest = database.query(
        """SELECT t.*, fc.title AS cat_title, fc.slug AS cat_slug, fc.icon AS cat_icon,
           (SELECT COUNT(*) FROM forum_posts p WHERE p.topic_id=t.id AND p.is_visible=1) AS replies
           FROM forum_topics t JOIN forum_categories fc ON fc.id=t.category_id
           WHERE t.is_visible=1 ORDER BY t.last_activity_at DESC, t.id DESC LIMIT 8""")
    total_topics = database.query(
        "SELECT COUNT(*) n FROM forum_topics WHERE is_visible=1", one=True)["n"]
    total_posts = database.query(
        "SELECT COUNT(*) n FROM forum_posts WHERE is_visible=1", one=True)["n"]
    return render_template("forum/index.html", cats=cats, latest=latest,
                           total_topics=total_topics, total_posts=total_posts,
                           page_title="انجمن‌های تخصصی")


@app.route("/forum/<slug>/")
def forum_category(slug):
    cat = database.query(
        "SELECT * FROM forum_categories WHERE slug=? AND is_visible=1", (slug,), one=True)
    if not cat:
        abort(404)
    q = request.args.get("q", "").strip()
    where, args = "WHERE t.category_id=? AND t.is_visible=1", [cat["id"]]
    if q:
        where += " AND (t.title LIKE ? OR t.content LIKE ?)"
        args += [f"%{q}%"] * 2
    topics = database.query(
        f"""SELECT t.*, (SELECT COUNT(*) FROM forum_posts p WHERE p.topic_id=t.id AND p.is_visible=1) AS replies
            FROM forum_topics t {where} ORDER BY t.is_pinned DESC, t.last_activity_at DESC, t.id DESC
            LIMIT 100""", args)
    cats = _forum_categories_with_counts()
    return render_template("forum/category.html", cat=cat, topics=topics, cats=cats, q=q,
                           page_title=f"انجمن {cat['title']}")


@app.route("/forum/topic/<int:tid>/")
def forum_topic(tid):
    topic = database.query(
        """SELECT t.*, fc.title AS cat_title, fc.slug AS cat_slug
           FROM forum_topics t JOIN forum_categories fc ON fc.id=t.category_id
           WHERE t.id=? AND t.is_visible=1""", (tid,), one=True)
    if not topic:
        abort(404)
    database.execute("UPDATE forum_topics SET views=views+1 WHERE id=?", (tid,))
    posts = database.query(
        "SELECT * FROM forum_posts WHERE topic_id=? AND is_visible=1 ORDER BY id", (tid,))
    return render_template("forum/topic.html", topic=topic, posts=posts,
                           page_title=topic["title"])


@app.route("/forum/new/<cat_slug>/", methods=["GET", "POST"])
@login_required
def forum_new_topic(cat_slug):
    cat = database.query(
        "SELECT * FROM forum_categories WHERE slug=? AND is_visible=1", (cat_slug,), one=True)
    if not cat:
        abort(404)
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        u = current_user()
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("عنوان و متن تاپیک الزامی است.", "error")
            return redirect(url_for("forum_new_topic", cat_slug=cat_slug))
        tid = database.execute(
            """INSERT INTO forum_topics (category_id, user_id, author_name, title, content)
               VALUES (?,?,?,?,?)""",
            (cat["id"], u["id"], u["full_name"], title, content))
        flash("تاپیک شما با موفقیت ایجاد شد. 🎉", "success")
        return redirect(url_for("forum_topic", tid=tid))
    return render_template("forum/new_topic.html", cat=cat, page_title=f"تاپیک جدید — {cat['title']}")


@app.route("/forum/topic/<int:tid>/reply", methods=["POST"])
@login_required
def forum_reply(tid):
    if not valid_csrf():
        abort(400)
    topic = database.query(
        "SELECT * FROM forum_topics WHERE id=? AND is_visible=1", (tid,), one=True)
    if not topic:
        abort(404)
    if topic["is_locked"]:
        flash("این تاپیک قفل شده است و امکان پاسخ جدید وجود ندارد.", "error")
        return redirect(url_for("forum_topic", tid=tid))
    u = current_user()
    content = request.form.get("content", "").strip()
    if not content:
        flash("متن پاسخ الزامی است.", "error")
        return redirect(url_for("forum_topic", tid=tid))
    database.execute(
        "INSERT INTO forum_posts (topic_id, user_id, author_name, content) VALUES (?,?,?,?)",
        (tid, u["id"], u["full_name"], content))
    database.execute(
        "UPDATE forum_topics SET last_activity_at=datetime('now','localtime') WHERE id=?", (tid,))
    flash("پاسخ شما ثبت شد.", "success")
    return redirect(url_for("forum_topic", tid=tid) + "#last-post")


# ==================================================================
# چت آنلاین هوشمند (پاسخ‌گوی سوالات سایت بر پایه مستندات)
# ==================================================================
CHAT_FALLBACK = (
    "متأسفانه پاسخ دقیقی برای این سوال در پایگاه دانش من پیدا نکردم. 🙏\n"
    "می‌توانید سوال را به شکل دیگری بپرسید یا از طریق «تماس با ما» سوال خود را ثبت کنید "
    "تا کارشناسان ما پاسخ دهند."
)

# قواعد هدایت (Intent) — هدایت کاربر به صفحه مناسب
CHAT_INTENTS = [
    (["نوبت", "رزرو", "وقت", "درخواست مشاوره", "مشاوره بگیرم", "مشاور آنلاین"],
     "برای دریافت نوبت مشاوره، فرم «درخواست مشاوره» را تکمیل کنید؛ کارشناسان ما در اسرع وقت با شما تماس می‌گیرند. 📅",
     [{"label": "درخواست مشاوره", "url": "/consultation/"}, {"label": "مراکز استانی", "url": "/centers/"}]),
    (["پیگیری", "کد پیگیری", "وضعیت درخواست", "درخواستم", "استعلام"],
     "برای پیگیری درخواست‌های خود (نوبت، همکاری، ثبت‌نام دوره) کد پیگیری را در صفحه پیگیری وارد کنید. 🔎",
     [{"label": "پیگیری درخواست", "url": "/tracking/"}]),
    (["دوره", "آموزش", "کارگاه", "وبینار", "کلاس", "ثبت نام دوره", "ثبت‌نام دوره"],
     "دوره‌های تخصصی و عمومی آکادمی رز را در صفحه دوره‌ها ببینید؛ می‌توانید بر اساس دسته‌بندی یا وضعیت (در حال ثبت‌نام، در حال برگزاری، رایگان) فیلتر کنید. 🎓",
     [{"label": "همه دوره‌ها", "url": "/courses/"}, {"label": "در حال ثبت‌نام", "url": "/courses/?tab=registration"}]),
    (["انجمن", "تالار", "گفتگو", "تاپیک", "پرسش و پاسخ کاربران"],
     "در انجمن‌های تخصصی رز می‌توانید تاپیک جدید بسازید، به بحث‌ها پاسخ دهید و تجربیات خود را به اشتراک بگذارید (نیاز به ورود به حساب کاربری دارد). 💬",
     [{"label": "انجمن‌های تخصصی", "url": "/forum/"}, {"label": "ورود / ثبت‌نام", "url": "/login/"}]),
    (["همکاری", "فراخوان", "راه اندازی مرکز", "راه‌اندازی مرکز", "تأسیس کلینیک", "تاسیس کلینیک"],
     "فراخوان همکاری مراکز مشاوره شامل ثبت اطلاعات کامل شما، مدارک و مشخصات ملک است؛ پس از بررسی، با شما تماس گرفته می‌شود. 🤝",
     [{"label": "فراخوان همکاری", "url": "/cooperation/"}]),
    (["تاریخ", "شمسی", "میلادی", "تبدیل تاریخ", "امروز چندمه"],
     "ابزار تبدیل تاریخ شمسی و میلادی سایت در دسترس شماست؛ همچنین API تبدیل تاریخ برای سامانه‌های دیگر موجود است. 📅",
     [{"label": "تبدیل تاریخ", "url": "/jalali/"}]),
    (["نقشه", "آدرس مرکز", "مرکز کجا", "کلینیک کجا", "لوکیشن", "نزدیک ترین مرکز", "نزدیک‌ترین مرکز"],
     "تمام مراکز و کلینیک‌های رز را روی نقشه ایران ببینید؛ با کلیک روی هر نشانگر، اطلاعات تماس و توانایی‌های آن مرکز نمایش داده می‌شود. 🗺",
     [{"label": "نقشه مراکز ایران", "url": "/map/"}]),
    (["ثبت مرکز", "ثبت کلینیک", "کلینیک جدید", "مرکز جدید", "نمایش کلینیک من"],
     "اگر مدیر یک مرکز یا کلینیک مشاوره هستید، اطلاعات مرکز خود را ثبت کنید تا پس از تأیید، روی نقشه و فهرست مراکز نمایش داده شود. ➕",
     [{"label": "ثبت مرکز / کلینیک", "url": "/centers/register/"}]),
    (["هیئت مدیره", "هیات مدیره", "مدیران", "اعضا", "بنیان گذار", "بنیان‌گذار"],
     "اعضای هیئت مدیره و تیم راهبری مجموعه رز را با سوابق و توانایی‌هایشان در صفحه هیئت مدیره ببینید. 👥",
     [{"label": "هیئت مدیره", "url": "/board/"}]),
    (["تماس", "شماره تماس", "ایمیل", "آدرس", "شماره تلفن", "راه های ارتباطی"],
     "راه‌های ارتباطی ما: تلفن، ایمیل و فرم تماس. از طریق هر کدام می‌توانید پیام خود را ارسال کنید. ✉️",
     [{"label": "تماس با ما", "url": "/contact/"}, {"label": "پیشنهاد و انتقاد", "url": "/feedback/"}]),
    (["ورود", "ثبت نام", "حساب کاربری", "رمز", "پنل کاربری", "لاگین", "لاگ‌این"],
     "با ساخت حساب کاربری می‌توانید درخواست‌های خود را مدیریت کنید، در دوره‌ها ثبت‌نام کنید و در انجمن‌ها فعالیت داشته باشید. 👤",
     [{"label": "ورود", "url": "/login/"}, {"label": "ثبت‌نام", "url": "/register/"}]),
    (["قیمت", "هزینه", "تعرفه", "چند", "تومان", "شهریه"],
     "قیمت هر دوره در صفحه دوره‌ها و جزئیات همان دوره مشخص است. هزینه خدمات مشاوره به نوع خدمت و مرکز بستگی دارد؛ برای اطلاع دقیق از طریق درخواست مشاوره اقدام کنید. 💰",
     [{"label": "دوره‌ها و قیمت‌ها", "url": "/courses/"}]),
    (["سلام", "درود", "خسته نباشید", "وقت بخیر", "aliak", "هی"],
     "سلام! 😊 خوش آمدید. من دستیار هوشمند مرکز رز هستم؛ درباره خدمات، دوره‌ها، نوبت‌دهی، مراکز یا هر بخش از سایت سوال دارید بپرسید.",
     []),
]

PERSIAN_STOPWORDS = {
    "از", "به", "با", "در", "که", "را", "و", "این", "آن", "برای", "است", "هست", "می",
    "چگونه", "چطور", "چه", "کجا", "کی", "چی", "چیست", "میخواهم", "می‌خواهم", "درباره",
    "شما", "من", "ما", "خود", "هم", "تا", "بر", "اگر", "باید", "کند", "کنم", "شود",
    "دارد", "دارم", "کردن", "شده", "بود", "باشد", "یک", "یکبار", "لطفا", "لطفاً",
}


def _normalize_fa(text):
    """نرمال‌سازی متن فارسی برای موتور جستجوی چت"""
    if not text:
        return ""
    s = str(text).lower()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("أ", "ا").replace("إ", "ا")
    s = s.replace("ؤ", "و").replace("ئ", "ی").replace("ة", "ه")
    s = s.replace("\u200c", " ")  # نیم‌فاصله
    s = re.sub(r"[^\w\s\u0600-\u06FF]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize_fa(text):
    tokens = _normalize_fa(text).split()
    return [t for t in tokens if t not in PERSIAN_STOPWORDS and len(t) > 1]


def _chat_score(question, doc):
    """امتیاز تطابق سوال با یک مستند پایگاه دانش"""
    q_tokens = _tokenize_fa(question)
    if not q_tokens:
        return 0.0
    doc_keywords = [k.strip() for k in (doc["keywords"] or "").split("،") if k.strip()]
    doc_keywords += [k.strip() for k in (doc["keywords"] or "").split(",") if k.strip()]
    doc_text = _normalize_fa(f"{doc['title']} {doc['title']} {doc['content'][:600]}")
    doc_tokens = set(_tokenize_fa(doc_text))
    q_norm = _normalize_fa(question)

    score = 0.0
    # ۱) کلیدواژه‌ها (وزن بالا) — تطابق زیررشته‌ای در سوال
    for kw in set(doc_keywords):
        kw_n = _normalize_fa(kw)
        if kw_n and (kw_n in q_norm or all(w in q_norm for w in kw_n.split() if w)):
            score += 3.0
    # ۲) هم‌پوشانی کلمات محتوا
    for t in q_tokens:
        if t in doc_tokens:
            score += 1.0
    # ۳) تطابق عنوان
    title_norm = _normalize_fa(doc["title"])
    for t in q_tokens:
        if t in title_norm:
            score += 0.8
    return score + (doc["priority"] or 0) * 0.5


def smart_chat_answer(question):
    """موتور پاسخ‌گویی هوشمند: برمی‌گرداند (answer, links, matched_title, score, answered)"""
    q = (question or "").strip()
    if not q:
        return CHAT_FALLBACK, [], "", 0.0, False

    # ۱) قواعد هدایت
    q_norm = _normalize_fa(q)
    best_intent = None
    for keys, answer, links in CHAT_INTENTS:
        for k in keys:
            k_n = _normalize_fa(k)
            if k_n and (k_n in q_norm or all(w in q_norm for w in k_n.split() if w)):
                if not best_intent or len(k_n) > best_intent[0]:
                    best_intent = (len(k_n), answer, links)
                break
    # ۲) مستندات پایگاه دانش
    docs = database.query("SELECT * FROM chat_documents WHERE is_active=1")
    best_doc, best_score = None, 0.0
    for d in docs:
        s = _chat_score(q, d)
        if s > best_score:
            best_doc, best_score = d, s

    # تصمیم نهایی
    if best_doc and best_score >= 2.5 and (not best_intent or best_score >= 4.5):
        links = []
        if best_doc["link"]:
            links.append({"label": best_doc["link_label"] or "مشاهده", "url": best_doc["link"]})
        database.execute(
            "UPDATE chat_documents SET hit_count=hit_count+1 WHERE id=?", (best_doc["id"],))
        return (f"{best_doc['content']}", links, best_doc["title"], best_score, True)
    if best_intent:
        return best_intent[1], best_intent[2], "قاعده هدایت: " + q_norm[:60], 2.0, True
    if best_doc and best_score >= 1.2:
        links = []
        if best_doc["link"]:
            links.append({"label": best_doc["link_label"] or "مشاهده", "url": best_doc["link"]})
        return best_doc["content"], links, best_doc["title"], best_score, True
    # ۳) پاسخ پیش‌فرض با پیشنهاد
    suggestions = [
        {"label": "درخواست مشاوره", "url": "/consultation/"},
        {"label": "دوره‌های آموزشی", "url": "/courses/"},
        {"label": "انجمن‌های تخصصی", "url": "/forum/"},
        {"label": "نقشه مراکز", "url": "/map/"},
        {"label": "تماس با ما", "url": "/contact/"},
    ]
    return CHAT_FALLBACK, [], "", best_score, False


@app.route("/chat/")
def chat_page():
    return render_template("chat.html", page_title="چت هوشمند")


@app.route("/chat/api/", methods=["POST"])
def chat_api():
    """API چت هوشمند — دریافت سوال و برگرداندن پاسخ + لینک‌های هدایت"""
    payload = request.get_json(silent=True) or request.form.to_dict()
    question = str(payload.get("message", "")).strip()
    session_key = str(payload.get("session_key", ""))[:64]
    if not question:
        return jsonify({"ok": False, "error": "سوال خالی است"}), 400
    if len(question) > 500:
        question = question[:500]
    answer, links, matched, score, answered = smart_chat_answer(question)
    try:
        database.execute(
            """INSERT INTO chat_logs (session_key, user_id, question, answer, matched_doc, score, is_answered)
               VALUES (?,?,?,?,?,?,?)""",
            (session_key, session.get("uid"), question, answer[:1000], matched, score,
             1 if answered else 0))
    except Exception:
        pass
    resp = {"ok": True, "answer": answer, "links": links, "answered": answered}
    return jsonify(resp)


# ==================================================================
# مراکز و کلینیک‌ها — نقشه ایران + جزئیات + ثبت مرکز
# ==================================================================
CENTER_CAPABILITIES = [
    "روان‌درمانی فردی", "زوج‌درمانی", "گروه‌درمانی", "مشاوره کودک و نوجوان",
    "نوروفیدبک", "واقعیت افزوده (VR)", "آزمون‌های روان‌شناختی", "مشاوره تلفنی و آنلاین",
    "کارگاه‌های آموزشی", "مشاوره شغلی و تحصیلی", "مداخله بحران", "مشاوره پیش از ازدواج",
]


@app.route("/map/")
def centers_map():
    kind = request.args.get("kind", "").strip()
    q = request.args.get("q", "").strip()
    where, args = "WHERE is_approved=1 AND lat IS NOT NULL AND lng IS NOT NULL", []
    if kind in ("مرکز استانی", "کلینیک"):
        where += " AND kind=?"
        args.append(kind)
    if q:
        where += " AND (province LIKE ? OR clinic_name LIKE ? OR address LIKE ? OR capabilities LIKE ?)"
        args += [f"%{q}%"] * 4
    rows = database.query(f"SELECT * FROM centers {where} ORDER BY sort_order, id", args)
    return render_template("map.html", centers=rows, kind=kind, q=q,
                           page_title="نقشه مراکز و کلینیک‌ها")


@app.route("/centers/<int:cid>/")
def center_detail(cid):
    center = database.query(
        "SELECT * FROM centers WHERE id=? AND is_approved=1", (cid,), one=True)
    if not center:
        abort(404)
    caps = [c.strip() for c in (center["capabilities"] or "").split("،") if c.strip()]
    near = database.query(
        """SELECT id, province, clinic_name, kind FROM centers
           WHERE is_approved=1 AND id!=? ORDER BY sort_order LIMIT 6""", (cid,))
    return render_template("center_detail.html", center=center, caps=caps, near=near,
                           page_title=center["clinic_name"] or f"مرکز {center['province']}")


@app.route("/centers/register/", methods=["GET", "POST"])
def center_register():
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        province = f.get("province", "").strip()
        clinic_name = f.get("clinic_name", "").strip()
        address = f.get("address", "").strip()
        submitter = f.get("submitter_name", "").strip()
        phone = jdate.en_digits(f.get("submitter_phone", "")).strip()
        caps = request.form.getlist("capabilities")
        if not province or not clinic_name or not address:
            flash("استان، نام مرکز و نشانی الزامی است.", "error")
            return redirect(url_for("center_register"))
        if not submitter or not validate_mobile(phone):
            flash("نام و شماره همراه ثبت‌کننده معتبر نیست.", "error")
            return redirect(url_for("center_register"))
        lat = f.get("lat", "").strip()
        lng = f.get("lng", "").strip()
        try:
            lat = float(jdate.en_digits(lat)) if lat else None
            lng = float(jdate.en_digits(lng)) if lng else None
        except ValueError:
            lat = lng = None
        database.execute(
            """INSERT INTO centers
               (province, clinic_name, address, clinic_phone, manager_name, work_hours,
                kind, lat, lng, capabilities, is_approved, submitter_name, submitter_phone,
                email, website)
               VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?,?)""",
            (province, clinic_name, address, jdate.en_digits(f.get("clinic_phone", "")).strip(),
             f.get("manager_name", "").strip(), f.get("work_hours", "").strip(),
             f.get("kind", "کلینیک").strip() or "کلینیک", lat, lng,
             "،".join(caps), submitter, phone,
             f.get("email", "").strip(), f.get("website", "").strip()))
        flash("اطلاعات مرکز شما ثبت شد و پس از بررسی و تأیید مدیریت، روی نقشه نمایش داده می‌شود. ✅", "success")
        return redirect(url_for("center_register"))
    return render_template("center_register.html", caps=CENTER_CAPABILITIES,
                           provinces=database.query(
                               "SELECT DISTINCT province FROM centers ORDER BY province"),
                           page_title="ثبت مرکز / کلینیک")


# ==================================================================
# اعضای هیئت مدیره
# ==================================================================
@app.route("/board/")
def board():
    rows = database.query(
        "SELECT * FROM board_members WHERE is_visible=1 ORDER BY sort_order, id")
    for r in rows:
        r["skills_list"] = [s.strip() for s in (r["skills"] or "").split("،") if s.strip()]
    return render_template("board.html", members=rows, page_title="هیئت مدیره")


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
            """INSERT INTO bookings (tracking_code, full_name, phone, service_type, center, note, source, user_id)
            VALUES (?,?,?,?,?,?, 'وب‌سایت', ?)""",
            (code, name, phone, service_type, f.get("center", "").strip(), f.get("note", "").strip(),
             session.get("uid")),
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
            row = database.query(
                "SELECT tracking_code, first_name, last_name, status, admin_note, created_at FROM hr_calls WHERE tracking_code=?",
                (code,), one=True)
            if row:
                result = dict(row)
                result["full_name"] = f"{row['first_name']} {row['last_name']}"
                result["service_type"] = "فراخوان همکاری"
                kind = "hr"
        if not result:
            row = database.query(
                """SELECT r.tracking_code, r.first_name, r.last_name, r.status, r.admin_note,
                          r.created_at, c.title AS course_title
                   FROM course_registrations r JOIN courses c ON c.id = r.course_id
                   WHERE r.tracking_code=?""", (code,), one=True)
            if row:
                result = dict(row)
                result["full_name"] = f"{row['first_name']} {row['last_name']}"
                result["service_type"] = f"ثبت‌نام دوره: {row['course_title']}"
                kind = "course"
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
# احراز هویت کاربران سایت
# ==================================================================
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/login/", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("panel"))
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        u = database.query("SELECT * FROM users WHERE email=?", (email,), one=True)
        if u and u["is_active"] and check_password_hash(u["password_hash"], password):
            session.clear()
            session["uid"] = u["id"]
            session["user_name"] = u["full_name"]
            register_session("user", u["full_name"], u["id"])
            database.execute("UPDATE users SET last_login_at=datetime('now','localtime') WHERE id=?",
                             (u["id"],))
            flash(f"خوش آمدید {u['full_name']} عزیز.", "success")
            nxt = request.args.get("next") or url_for("panel")
            if not nxt.startswith("/"):
                nxt = url_for("panel")
            return redirect(nxt)
        msg = "حساب کاربری شما غیرفعال است." if (u and not u["is_active"]) else "ایمیل یا گذرواژه نادرست است."
        flash(msg, "error")
    return render_template("login.html", page_title="ورود به حساب کاربری")


@app.route("/register/", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("panel"))
    if request.method == "POST":
        if not valid_csrf():
            abort(400)
        f = request.form
        name = f.get("full_name", "").strip()
        email = f.get("email", "").strip().lower()
        phone = jdate.en_digits(f.get("phone", "")).strip()
        p1, p2 = f.get("password", ""), f.get("password2", "")
        ok = True
        if not name:
            flash("نام و نام خانوادگی الزامی است.", "error"); ok = False
        if not EMAIL_RE.match(email):
            flash("ایمیل وارد شده معتبر نیست.", "error"); ok = False
        elif database.query("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("این ایمیل قبلاً ثبت شده است.", "error"); ok = False
        if phone and not (phone.startswith("09") and len(phone) == 11 and phone.isdigit()):
            flash("شماره همراه باید ۱۱ رقم و با ۰۹ شروع شود.", "error"); ok = False
        if len(p1) < 6:
            flash("گذرواژه باید حداقل ۶ کاراکتر باشد.", "error"); ok = False
        elif p1 != p2:
            flash("تکرار گذرواژه مطابقت ندارد.", "error"); ok = False
        if not check_captcha():
            flash("پاسخ کپچا نادرست است.", "error"); ok = False
        if ok:
            uid = database.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (?,?,?,?)",
                (name, email, phone, generate_password_hash(p1)))
            session.clear()
            session["uid"] = uid
            session["user_name"] = name
            register_session("user", name, uid)
            flash("حساب کاربری شما با موفقیت ایجاد شد. خوش آمدید!", "success")
            return redirect(url_for("panel"))
        return redirect(url_for("register", **{k: v for k, v in [("email", email), ("full_name", name)] }))
    generate_captcha()
    return render_template("register.html", page_title="ثبت‌نام در سایت")


@app.route("/logout/")
def logout():
    end_session()
    session.clear()
    flash("از حساب خود خارج شدید.", "success")
    return redirect(url_for("home"))


@app.route("/panel/")
@login_required
def panel():
    u = current_user()
    my_bookings = database.query(
        "SELECT * FROM bookings WHERE user_id=? OR phone=? ORDER BY id DESC LIMIT 20",
        (u["id"], u["phone"]))
    my_regs = database.query(
        """SELECT r.*, c.title AS course_title, c.slug AS course_slug
           FROM course_registrations r JOIN courses c ON c.id=r.course_id
           WHERE r.user_id=? OR r.mobile=? ORDER BY r.id DESC LIMIT 20""",
        (u["id"], u["phone"]))
    return render_template("panel.html", u=u, bookings=my_bookings, regs=my_regs,
                           page_title="پنل کاربری")


@app.route("/panel/profile", methods=["POST"])
@login_required
def panel_profile():
    u = current_user()
    name = request.form.get("full_name", "").strip()
    phone = jdate.en_digits(request.form.get("phone", "")).strip()
    if not name:
        flash("نام الزامی است.", "error")
        return redirect(url_for("panel"))
    if phone and not (phone.startswith("09") and len(phone) == 11 and phone.isdigit()):
        flash("شماره همراه معتبر نیست.", "error")
        return redirect(url_for("panel"))
    new_pw = request.form.get("new_password", "")
    if new_pw:
        if len(new_pw) < 6:
            flash("گذرواژه جدید باید حداقل ۶ کاراکتر باشد.", "error")
            return redirect(url_for("panel"))
        database.execute("UPDATE users SET full_name=?, phone=?, password_hash=? WHERE id=?",
                         (name, phone, generate_password_hash(new_pw), u["id"]))
    else:
        database.execute("UPDATE users SET full_name=?, phone=? WHERE id=?", (name, phone, u["id"]))
    session["user_name"] = name
    flash("پروفایل به‌روزرسانی شد.", "success")
    return redirect(url_for("panel"))


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
            session.clear()
            session["admin_id"] = u["id"]
            session["admin_name"] = u["full_name"]
            register_session("admin", u["full_name"], None)
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("نام کاربری یا گذرواژه نادرست است.", "error")
    return render_template("admin/login.html", page_title="ورود مدیریت")


@app.route("/admin/logout")
def admin_logout():
    end_session()
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
        "hr_calls": database.query("SELECT COUNT(*) n FROM hr_calls", one=True)["n"],
        "hr_calls_new": database.query("SELECT COUNT(*) n FROM hr_calls WHERE status='در انتظار بررسی'", one=True)["n"],
        "courses": database.query("SELECT COUNT(*) n FROM courses", one=True)["n"],
        "course_regs": database.query("SELECT COUNT(*) n FROM course_registrations", one=True)["n"],
        "course_regs_new": database.query("SELECT COUNT(*) n FROM course_registrations WHERE status='در انتظار بررسی'", one=True)["n"],
        "messages": database.query("SELECT COUNT(*) n FROM contact_messages", one=True)["n"],
        "messages_unread": database.query("SELECT COUNT(*) n FROM contact_messages WHERE is_read=0", one=True)["n"],
        "feedbacks": database.query("SELECT COUNT(*) n FROM feedbacks", one=True)["n"],
        "feedbacks_unread": database.query("SELECT COUNT(*) n FROM feedbacks WHERE is_read=0", one=True)["n"],
        "news": database.query("SELECT COUNT(*) n FROM news", one=True)["n"],
        "centers": database.query("SELECT COUNT(*) n FROM centers", one=True)["n"],
        "faqs": database.query("SELECT COUNT(*) n FROM faqs", one=True)["n"],
        "testimonials": database.query("SELECT COUNT(*) n FROM testimonials", one=True)["n"],
        "users": database.query("SELECT COUNT(*) n FROM users", one=True)["n"],
        "api_keys": database.query("SELECT COUNT(*) n FROM api_keys WHERE is_active=1", one=True)["n"],
        "api_requests": database.query("SELECT COALESCE(SUM(request_count),0) n FROM api_keys", one=True)["n"],
        "online": database.query(
            "SELECT COUNT(*) n FROM user_sessions WHERE is_active=1 AND last_seen_at >= datetime('now','localtime','-5 minutes')",
            one=True)["n"],
        "forum_topics": database.query("SELECT COUNT(*) n FROM forum_topics WHERE is_visible=1", one=True)["n"],
        "forum_posts": database.query("SELECT COUNT(*) n FROM forum_posts WHERE is_visible=1", one=True)["n"],
        "chat_docs": database.query("SELECT COUNT(*) n FROM chat_documents WHERE is_active=1", one=True)["n"],
        "chat_questions": database.query("SELECT COUNT(*) n FROM chat_logs", one=True)["n"],
        "chat_unanswered": database.query(
            "SELECT COUNT(*) n FROM chat_logs WHERE is_answered=0", one=True)["n"],
        "centers_pending": database.query(
            "SELECT COUNT(*) n FROM centers WHERE is_approved=0", one=True)["n"],
        "board_members": database.query("SELECT COUNT(*) n FROM board_members", one=True)["n"],
        "centers_on_map": database.query(
            "SELECT COUNT(*) n FROM centers WHERE is_approved=1 AND lat IS NOT NULL AND lng IS NOT NULL", one=True)["n"],
    }
    latest_bookings = database.query("SELECT * FROM bookings ORDER BY id DESC LIMIT 6")
    latest_messages = database.query("SELECT * FROM contact_messages ORDER BY id DESC LIMIT 6")
    latest_hr = database.query("SELECT * FROM hr_calls ORDER BY id DESC LIMIT 6")
    latest_regs = database.query(
        """SELECT r.*, c.title AS course_title FROM course_registrations r
           JOIN courses c ON c.id = r.course_id ORDER BY r.id DESC LIMIT 6""")
    online_now = database.query(
        """SELECT kind, display_name, last_seen_at FROM user_sessions
           WHERE is_active=1 AND last_seen_at >= datetime('now','localtime','-5 minutes')
           ORDER BY last_seen_at DESC LIMIT 8""")
    return render_template("admin/dashboard.html", stats=stats,
                           latest_bookings=latest_bookings, latest_messages=latest_messages,
                           latest_hr=latest_hr, latest_regs=latest_regs, online_now=online_now,
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


# ---------- مدیریت فراخوان‌های همکاری (فرم کامل) ----------
@app.route("/admin/hr-calls")
@admin_required
def admin_hr_calls():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    where, args = "WHERE 1=1", []
    if q:
        where += " AND (first_name LIKE ? OR last_name LIKE ? OR national_code LIKE ? OR tracking_code LIKE ? OR mobile LIKE ?)"
        args += [f"%{q}%"] * 5
    if status:
        where += " AND status=?"
        args.append(status)
    rows = database.query(f"SELECT * FROM hr_calls {where} ORDER BY id DESC", args)
    return render_template("admin/hr_calls.html", rows=rows, q=q, status=status,
                           page_title="فراخوان‌های همکاری")


@app.route("/admin/hr-calls/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_hr_call_detail(rid):
    row = database.query("SELECT * FROM hr_calls WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        database.execute(
            "UPDATE hr_calls SET status=?, admin_note=? WHERE id=?",
            (request.form.get("status", row["status"]),
             request.form.get("admin_note", ""), rid))
        flash("وضعیت فراخوان به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_hr_call_detail", rid=rid))
    return render_template("admin/hr_call_detail.html", row=row, page_title="جزئیات فراخوان همکاری")


@app.route("/admin/hr-calls/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_hr_call_delete(rid):
    row = database.query("SELECT * FROM hr_calls WHERE id=?", (rid,), one=True)
    if row:
        # حذف فایل‌های پیوست
        for col in ["military_file", "education_file", "license_file",
                    "center_license_file", "center_permit_file", "property_file",
                    "national_card_file"]:
            fname = row[col]
            if fname:
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                except OSError:
                    pass
        database.execute("DELETE FROM hr_calls WHERE id=?", (rid,))
    flash("فراخوان و فایل‌های پیوست آن حذف شد.", "success")
    return redirect(url_for("admin_hr_calls"))


@app.route("/admin/uploads/<path:filename>")
@admin_required
def admin_upload_file(filename):
    """دریافت فایل‌های آپلودی فقط توسط مدیریت"""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


# ---------- مدیریت دوره‌های آموزشی ----------
@app.route("/admin/courses")
@admin_required
def admin_courses():
    rows = database.query(
        """SELECT c.*, COUNT(r.id) AS regs FROM courses c
           LEFT JOIN course_registrations r ON r.course_id = c.id
           GROUP BY c.id ORDER BY c.sort_order, c.id DESC""")
    return render_template("admin/courses.html", rows=rows, page_title="مدیریت دوره‌ها")


def _slugify_course(title, existing_id=None):
    base = title.strip().replace(" ", "-")[:40] or "course"
    slug = base
    n = 1
    while True:
        row = database.query("SELECT id FROM courses WHERE slug=?", (slug,), one=True)
        if not row or (existing_id and row["id"] == existing_id):
            return slug
        n += 1
        slug = f"{base}-{n}"


@app.route("/admin/courses/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_course_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("عنوان دوره الزامی است.", "error")
            return redirect(url_for("admin_course_new"))
        slug = _slugify_course(title)
        cat_raw = request.form.get("category_id", "").strip()
        database.execute(
            """INSERT INTO courses
            (slug, title, summary, content, teacher, price, duration, capacity,
             start_date, schedule, level, is_open, sort_order,
             category_id, status, rating, votes, students, price_num, is_free, is_special, thumb)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (slug, title, request.form.get("summary", "").strip(),
             request.form.get("content", "").strip(), request.form.get("teacher", "").strip(),
             request.form.get("price", "رایگان").strip(), request.form.get("duration", "").strip(),
             request.form.get("capacity", 0, type=int), request.form.get("start_date", "").strip(),
             request.form.get("schedule", "").strip(), request.form.get("level", "عمومی").strip(),
             1 if request.form.get("is_open") else 0,
             request.form.get("sort_order", 0, type=int),
             int(cat_raw) if cat_raw.isdigit() else None,
             request.form.get("status", "registration").strip(),
             request.form.get("rating", 4.5, type=float),
             request.form.get("votes", 0, type=int),
             request.form.get("students", 0, type=int),
             request.form.get("price_num", 0, type=int),
             1 if request.form.get("is_free") else 0,
             1 if request.form.get("is_special") else 0,
             request.form.get("thumb", "🎓").strip() or "🎓"))
        flash("دوره جدید ایجاد شد.", "success")
        return redirect(url_for("admin_courses"))
    cats = database.query("SELECT * FROM course_categories ORDER BY sort_order")
    return render_template("admin/course_form.html", row=None, cats=cats,
                           status_labels=COURSE_STATUS_LABELS, page_title="دوره جدید")


@app.route("/admin/courses/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_course_edit(rid):
    row = database.query("SELECT * FROM courses WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("عنوان دوره الزامی است.", "error")
            return redirect(url_for("admin_course_edit", rid=rid))
        cat_raw = request.form.get("category_id", "").strip()
        database.execute(
            """UPDATE courses SET title=?, summary=?, content=?, teacher=?, price=?, duration=?,
               capacity=?, start_date=?, schedule=?, level=?, is_open=?, sort_order=?,
               category_id=?, status=?, rating=?, votes=?, students=?, price_num=?,
               is_free=?, is_special=?, thumb=? WHERE id=?""",
            (title, request.form.get("summary", "").strip(),
             request.form.get("content", "").strip(), request.form.get("teacher", "").strip(),
             request.form.get("price", "رایگان").strip(), request.form.get("duration", "").strip(),
             request.form.get("capacity", 0, type=int), request.form.get("start_date", "").strip(),
             request.form.get("schedule", "").strip(), request.form.get("level", "عمومی").strip(),
             1 if request.form.get("is_open") else 0,
             request.form.get("sort_order", 0, type=int),
             int(cat_raw) if cat_raw.isdigit() else None,
             request.form.get("status", "registration").strip(),
             request.form.get("rating", 4.5, type=float),
             request.form.get("votes", 0, type=int),
             request.form.get("students", 0, type=int),
             request.form.get("price_num", 0, type=int),
             1 if request.form.get("is_free") else 0,
             1 if request.form.get("is_special") else 0,
             request.form.get("thumb", "🎓").strip() or "🎓", rid))
        flash("دوره به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_courses"))
    cats = database.query("SELECT * FROM course_categories ORDER BY sort_order")
    return render_template("admin/course_form.html", row=row, cats=cats,
                           status_labels=COURSE_STATUS_LABELS, page_title="ویرایش دوره")


@app.route("/admin/courses/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_course_delete(rid):
    database.execute("DELETE FROM course_registrations WHERE course_id=?", (rid,))
    database.execute("DELETE FROM courses WHERE id=?", (rid,))
    flash("دوره و ثبت‌نام‌های آن حذف شد.", "success")
    return redirect(url_for("admin_courses"))


# ---------- ثبت‌نام‌های دوره‌ها ----------
@app.route("/admin/course-regs")
@admin_required
def admin_course_regs():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    where, args = "WHERE 1=1", []
    if q:
        where += " AND (r.first_name LIKE ? OR r.last_name LIKE ? OR r.national_code LIKE ? OR r.tracking_code LIKE ? OR r.mobile LIKE ?)"
        args += [f"%{q}%"] * 5
    if status:
        where += " AND r.status=?"
        args.append(status)
    rows = database.query(
        f"""SELECT r.*, c.title AS course_title FROM course_registrations r
            JOIN courses c ON c.id = r.course_id {where} ORDER BY r.id DESC""", args)
    return render_template("admin/course_regs.html", rows=rows, q=q, status=status,
                           page_title="ثبت‌نام‌های دوره‌ها")


@app.route("/admin/course-regs/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_course_reg_detail(rid):
    row = database.query(
        """SELECT r.*, c.title AS course_title, c.teacher, c.schedule FROM course_registrations r
           JOIN courses c ON c.id = r.course_id WHERE r.id=?""", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        database.execute(
            "UPDATE course_registrations SET status=?, admin_note=? WHERE id=?",
            (request.form.get("status", row["status"]),
             request.form.get("admin_note", ""), rid))
        flash("وضعیت ثبت‌نام به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_course_reg_detail", rid=rid))
    return render_template("admin/course_reg_detail.html", row=row, page_title="جزئیات ثبت‌نام")


@app.route("/admin/course-regs/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_course_reg_delete(rid):
    database.execute("DELETE FROM course_registrations WHERE id=?", (rid,))
    flash("ثبت‌نام حذف شد.", "success")
    return redirect(url_for("admin_course_regs"))


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


# ---------- مدیریت مراکز استانی و کلینیک‌ها ----------
@app.route("/admin/centers")
@admin_required
def admin_centers():
    kind = request.args.get("kind", "").strip()
    q = request.args.get("q", "").strip()
    where, args = "WHERE 1=1", []
    if kind in ("مرکز استانی", "کلینیک"):
        where += " AND kind=?"
        args.append(kind)
    if q:
        where += " AND (province LIKE ? OR clinic_name LIKE ? OR address LIKE ?)"
        args += [f"%{q}%"] * 3
    rows = database.query(
        f"SELECT * FROM centers {where} ORDER BY is_approved, is_soon, sort_order", args)
    pending = database.query("SELECT COUNT(*) n FROM centers WHERE is_approved=0", one=True)["n"]
    return render_template("admin/centers.html", rows=rows, kind=kind, q=q, pending=pending,
                           page_title="مدیریت مراکز و کلینیک‌ها")


@app.route("/admin/centers/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_centers_new():
    if request.method == "POST":
        f = request.form
        if not f.get("province", "").strip():
            flash("نام استان الزامی است.", "error")
            return redirect(request.url)
        lat = f.get("lat", "").strip()
        lng = f.get("lng", "").strip()
        try:
            lat = float(jdate.en_digits(lat)) if lat else None
            lng = float(jdate.en_digits(lng)) if lng else None
        except ValueError:
            lat = lng = None
        caps = f.get("capabilities", "").strip()
        database.execute(
            """INSERT INTO centers (province, clinic_name, address, postal_code, clinic_phone,
            manager_name, manager_phone, exec_name, exec_phone, work_hours, map_url, is_soon, sort_order,
            kind, lat, lng, capabilities, is_approved, email, website)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f.get("province", "").strip(), f.get("clinic_name", "").strip(),
             f.get("address", "").strip(), f.get("postal_code", "").strip(),
             f.get("clinic_phone", "").strip(), f.get("manager_name", "").strip(),
             f.get("manager_phone", "").strip(), f.get("exec_name", "").strip(),
             f.get("exec_phone", "").strip(), f.get("work_hours", "").strip(),
             f.get("map_url", "").strip(), 1 if f.get("is_soon") else 0,
             f.get("sort_order", 0, type=int),
             f.get("kind", "مرکز استانی").strip() or "مرکز استانی", lat, lng,
             caps, 1 if f.get("is_approved", "on") else 0,
             f.get("email", "").strip(), f.get("website", "").strip()))
        flash("مرکز جدید اضافه شد.", "success")
        return redirect(url_for("admin_centers"))
    return render_template("admin/center_form.html", item=None, caps=CENTER_CAPABILITIES,
                           page_title="مرکز جدید")


@app.route("/admin/centers/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_centers_edit(rid):
    row = database.query("SELECT * FROM centers WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        f = request.form
        lat = f.get("lat", "").strip()
        lng = f.get("lng", "").strip()
        try:
            lat = float(jdate.en_digits(lat)) if lat else None
            lng = float(jdate.en_digits(lng)) if lng else None
        except ValueError:
            lat = lng = None
        database.execute(
            """UPDATE centers SET province=?, clinic_name=?, address=?, postal_code=?,
            clinic_phone=?, manager_name=?, manager_phone=?, exec_name=?, exec_phone=?,
            work_hours=?, map_url=?, is_soon=?, sort_order=?, kind=?, lat=?, lng=?,
            capabilities=?, is_approved=?, email=?, website=? WHERE id=?""",
            (f.get("province", "").strip(), f.get("clinic_name", "").strip(),
             f.get("address", "").strip(), f.get("postal_code", "").strip(),
             f.get("clinic_phone", "").strip(), f.get("manager_name", "").strip(),
             f.get("manager_phone", "").strip(), f.get("exec_name", "").strip(),
             f.get("exec_phone", "").strip(), f.get("work_hours", "").strip(),
             f.get("map_url", "").strip(), 1 if f.get("is_soon") else 0,
             f.get("sort_order", 0, type=int),
             f.get("kind", "مرکز استانی").strip() or "مرکز استانی", lat, lng,
             f.get("capabilities", "").strip(), 1 if f.get("is_approved") else 0,
             f.get("email", "").strip(), f.get("website", "").strip(), rid))
        flash("مرکز به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_centers"))
    return render_template("admin/center_form.html", item=row, caps=CENTER_CAPABILITIES,
                           page_title="ویرایش مرکز")


@app.route("/admin/centers/<int:rid>/approve", methods=["POST"])
@admin_required
@admin_csrf
def admin_center_approve(rid):
    row = database.query("SELECT * FROM centers WHERE id=?", (rid,), one=True)
    if row:
        new_state = 0 if row["is_approved"] else 1
        database.execute("UPDATE centers SET is_approved=? WHERE id=?", (new_state, rid))
        flash("مرکز تأیید شد و روی نقشه و فهرست مراکز نمایش داده می‌شود." if new_state
              else "نمایش مرکز غیرفعال شد.", "success")
    return redirect(url_for("admin_centers"))


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


# ---------- مدیریت کاربران سایت ----------
@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    where, args = "WHERE 1=1", []
    if q:
        where += " AND (full_name LIKE ? OR email LIKE ? OR phone LIKE ?)"
        args += [f"%{q}%"] * 3
    rows = database.query(
        f"""SELECT u.*,
              (SELECT COUNT(*) FROM user_sessions s WHERE s.user_id=u.id AND s.is_active=1) AS online_sessions,
              (SELECT COUNT(*) FROM bookings b WHERE b.user_id=u.id) AS bookings_count
            FROM users u {where} ORDER BY u.id DESC""", args)
    return render_template("admin/users.html", rows=rows, q=q, page_title="مدیریت کاربران")


@app.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_user_new():
    if request.method == "POST":
        f = request.form
        name = f.get("full_name", "").strip()
        email = f.get("email", "").strip().lower()
        pw = f.get("password", "")
        if not name or not EMAIL_RE.match(email):
            flash("نام و ایمیل معتبر الزامی است.", "error")
            return redirect(request.url)
        if database.query("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("این ایمیل قبلاً ثبت شده است.", "error")
            return redirect(request.url)
        if len(pw) < 6:
            flash("گذرواژه باید حداقل ۶ کاراکتر باشد.", "error")
            return redirect(request.url)
        database.execute(
            """INSERT INTO users (full_name, email, phone, password_hash, is_active)
               VALUES (?,?,?,?,?)""",
            (name, email, jdate.en_digits(f.get("phone", "")).strip(),
             generate_password_hash(pw), 1 if f.get("is_active") else 0))
        flash("کاربر جدید ایجاد شد.", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin/user_form.html", row=None, page_title="کاربر جدید")


@app.route("/admin/users/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_user_edit(rid):
    row = database.query("SELECT * FROM users WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        f = request.form
        name = f.get("full_name", "").strip()
        email = f.get("email", "").strip().lower()
        if not name or not EMAIL_RE.match(email):
            flash("نام و ایمیل معتبر الزامی است.", "error")
            return redirect(request.url)
        dup = database.query("SELECT id FROM users WHERE email=? AND id!=?", (email, rid), one=True)
        if dup:
            flash("این ایمیل برای کاربر دیگری ثبت شده است.", "error")
            return redirect(request.url)
        pw = f.get("password", "")
        if pw:
            if len(pw) < 6:
                flash("گذرواژه باید حداقل ۶ کاراکتر باشد.", "error")
                return redirect(request.url)
            database.execute(
                """UPDATE users SET full_name=?, email=?, phone=?, password_hash=?, is_active=?
                   WHERE id=?""",
                (name, email, jdate.en_digits(f.get("phone", "")).strip(),
                 generate_password_hash(pw), 1 if f.get("is_active") else 0, rid))
        else:
            database.execute(
                "UPDATE users SET full_name=?, email=?, phone=?, is_active=? WHERE id=?",
                (name, email, jdate.en_digits(f.get("phone", "")).strip(),
                 1 if f.get("is_active") else 0, rid))
        if not f.get("is_active"):
            # غیرفعال‌سازی: بستن همه سشن‌های فعال این کاربر
            database.execute(
                "UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime') WHERE user_id=? AND is_active=1",
                (rid,))
        flash("اطلاعات کاربر به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin/user_form.html", row=row, page_title="ویرایش کاربر")


@app.route("/admin/users/<int:rid>/toggle", methods=["POST"])
@admin_required
@admin_csrf
def admin_user_toggle(rid):
    row = database.query("SELECT * FROM users WHERE id=?", (rid,), one=True)
    if row:
        new_state = 0 if row["is_active"] else 1
        database.execute("UPDATE users SET is_active=? WHERE id=?", (new_state, rid))
        if not new_state:
            database.execute(
                """UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime')
                   WHERE user_id=? AND is_active=1""", (rid,))
        flash("وضعیت کاربر تغییر کرد.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_user_delete(rid):
    database.execute(
        """UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime')
           WHERE user_id=? AND is_active=1""", (rid,))
    database.execute("DELETE FROM users WHERE id=?", (rid,))
    flash("کاربر حذف شد.", "success")
    return redirect(url_for("admin_users"))


# ---------- نمایش افراد لاگین‌شده ----------
@app.route("/admin/sessions")
@admin_required
def admin_sessions():
    # سشن‌های بی‌فعالیت قدیمی (بیش از ۷ روز) را می‌بندیم
    database.execute(
        """UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime')
           WHERE is_active=1 AND last_seen_at < datetime('now','localtime','-7 days')""")
    active = database.query(
        """SELECT s.*, CASE WHEN s.user_id IS NOT NULL THEN
             (SELECT full_name FROM users u WHERE u.id=s.user_id)
             ELSE s.display_name END AS person
           FROM user_sessions s WHERE s.is_active=1
           ORDER BY s.last_seen_at DESC LIMIT 300""")
    history = database.query(
        """SELECT s.*, CASE WHEN s.user_id IS NOT NULL THEN
             (SELECT full_name FROM users u WHERE u.id=s.user_id)
             ELSE s.display_name END AS person
           FROM user_sessions s WHERE s.is_active=0
           ORDER BY s.logout_at DESC, s.last_seen_at DESC LIMIT 100""")
    online_count = 0
    now = datetime.datetime.now()
    for r in active:
        try:
            seen = datetime.datetime.strptime(r["last_seen_at"], "%Y-%m-%d %H:%M:%S")
            if (now - seen).total_seconds() <= ONLINE_WINDOW:
                online_count += 1
        except ValueError:
            pass
    online_cutoff = (now - datetime.timedelta(seconds=ONLINE_WINDOW)).strftime("%Y-%m-%d %H:%M:%S")
    return render_template("admin/sessions.html", active=active, history=history,
                           online_count=online_count, online_cutoff=online_cutoff,
                           page_title="افراد لاگین‌شده")


@app.route("/admin/sessions/<int:rid>/logout", methods=["POST"])
@admin_required
@admin_csrf
def admin_session_logout(rid):
    row = database.query("SELECT sid FROM user_sessions WHERE id=?", (rid,), one=True)
    if row:
        database.execute(
            """UPDATE user_sessions SET is_active=0, logout_at=datetime('now','localtime')
               WHERE sid=? AND is_active=1""", (row["sid"],))
    flash("سشن کاربر بسته شد و کاربر از سامانه خارج گردید.", "success")
    return redirect(url_for("admin_sessions"))


# ---------- بلوک‌های صفحه اصلی ----------
@app.route("/admin/blocks")
@admin_required
def admin_blocks():
    rows = database.query("SELECT * FROM home_blocks ORDER BY sort_order, id")
    kinds = HOME_BLOCK_KINDS
    return render_template("admin/blocks.html", rows=rows, kinds=kinds,
                           QUICK_FORMS=QUICK_FORMS, page_title="بلوک‌های صفحه اصلی")


def _news_options():
    return database.query(
        "SELECT id, title FROM news ORDER BY id DESC LIMIT 100")


def _course_options():
    return database.query("SELECT id, title FROM courses ORDER BY sort_order, id DESC")


def _block_fields(f):
    """استخراج مقادیر ref_id و link بر اساس نوع بلوک از فرم ادمین"""
    kind = f.get("kind", "custom")
    ref_raw = ""
    link = ""
    if kind == "article":
        ref_raw = f.get("ref_id_article", "").strip()
    elif kind == "course":
        ref_raw = f.get("ref_id_course", "").strip()
    elif kind == "form":
        link = f.get("quick_link", "").strip()
    else:
        link = f.get("link_custom", "").strip()
    ref_id = int(ref_raw) if ref_raw.isdigit() else None
    return kind, link, ref_id


@app.route("/admin/blocks/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_block_new():
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("عنوان بلوک الزامی است.", "error")
            return redirect(request.url)
        kind, link, ref_id = _block_fields(f)
        mx = database.query("SELECT MAX(sort_order) m FROM home_blocks", one=True)["m"] or 0
        database.execute(
            """INSERT INTO home_blocks (kind, title, subtitle, icon, link, ref_id, sort_order, is_visible)
               VALUES (?,?,?,?,?,?,?,?)""",
            (kind, title, f.get("subtitle", "").strip(),
             f.get("icon", "✨").strip() or "✨", link, ref_id, mx + 1,
             1 if f.get("is_visible") else 0))
        flash("بلوک جدید اضافه شد و در صفحه اصلی نمایش داده می‌شود.", "success")
        return redirect(url_for("admin_blocks"))
    return render_template("admin/block_form.html", row=None, kinds=HOME_BLOCK_KINDS,
                           QUICK_FORMS=QUICK_FORMS, news_opts=_news_options(),
                           course_opts=_course_options(), page_title="بلوک جدید")


@app.route("/admin/blocks/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_block_edit(rid):
    row = database.query("SELECT * FROM home_blocks WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("عنوان بلوک الزامی است.", "error")
            return redirect(request.url)
        kind, link, ref_id = _block_fields(f)
        database.execute(
            """UPDATE home_blocks SET kind=?, title=?, subtitle=?, icon=?, link=?, ref_id=?,
               sort_order=?, is_visible=? WHERE id=?""",
            (kind, title, f.get("subtitle", "").strip(),
             f.get("icon", "✨").strip() or "✨", link, ref_id,
             f.get("sort_order", 0, type=int), 1 if f.get("is_visible") else 0, rid))
        flash("بلوک به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_blocks"))
    return render_template("admin/block_form.html", row=row, kinds=HOME_BLOCK_KINDS,
                           QUICK_FORMS=QUICK_FORMS, news_opts=_news_options(),
                           course_opts=_course_options(), page_title="ویرایش بلوک")


@app.route("/admin/blocks/<int:rid>/toggle", methods=["POST"])
@admin_required
@admin_csrf
def admin_block_toggle(rid):
    database.execute("UPDATE home_blocks SET is_visible = 1 - is_visible WHERE id=?", (rid,))
    return redirect(url_for("admin_blocks"))


@app.route("/admin/blocks/<int:rid>/move", methods=["POST"])
@admin_required
@admin_csrf
def admin_block_move(rid):
    direction = request.form.get("dir", "up")
    row = database.query("SELECT * FROM home_blocks WHERE id=?", (rid,), one=True)
    if row:
        if direction == "up":
            other = database.query(
                "SELECT * FROM home_blocks WHERE sort_order<=? AND id!=? ORDER BY sort_order DESC, id DESC LIMIT 1",
                (row["sort_order"], rid), one=True)
        else:
            other = database.query(
                "SELECT * FROM home_blocks WHERE sort_order>=? AND id!=? ORDER BY sort_order, id LIMIT 1",
                (row["sort_order"], rid), one=True)
        if other:
            database.execute("UPDATE home_blocks SET sort_order=? WHERE id=?",
                             (row["sort_order"], other["id"]))
            database.execute("UPDATE home_blocks SET sort_order=? WHERE id=?",
                             (other["sort_order"], rid))
    return redirect(url_for("admin_blocks"))


@app.route("/admin/blocks/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_block_delete(rid):
    database.execute("DELETE FROM home_blocks WHERE id=?", (rid,))
    flash("بلوک حذف شد.", "success")
    return redirect(url_for("admin_blocks"))


# ---------- کلیدهای API سامانه‌های خارجی ----------
def _gen_api_key():
    return "rc_" + secrets.token_hex(24)


@app.route("/admin/api-keys")
@admin_required
def admin_api_keys():
    rows = database.query("SELECT * FROM api_keys ORDER BY id DESC")
    return render_template("admin/api_keys.html", rows=rows, page_title="کلیدهای API")


@app.route("/admin/api-keys/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_api_key_new():
    name = request.form.get("name", "").strip()
    if not name:
        flash("نام سامانه/سازمان الزامی است.", "error")
        return redirect(url_for("admin_api_keys"))
    key = _gen_api_key()
    database.execute(
        "INSERT INTO api_keys (name, key, note) VALUES (?,?,?)",
        (name, key, request.form.get("note", "").strip()))
    flash(f"کلید API جدید ساخته شد. کلید فقط همین یک بار نمایش داده می‌شود:", "success")
    return render_template("admin/api_keys.html", rows=database.query("SELECT * FROM api_keys ORDER BY id DESC"),
                           new_key=key, new_key_name=name, page_title="کلیدهای API")


@app.route("/admin/api-keys/<int:rid>/toggle", methods=["POST"])
@admin_required
@admin_csrf
def admin_api_key_toggle(rid):
    database.execute("UPDATE api_keys SET is_active = 1 - is_active WHERE id=?", (rid,))
    flash("وضعیت کلید تغییر کرد.", "success")
    return redirect(url_for("admin_api_keys"))


@app.route("/admin/api-keys/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_api_key_delete(rid):
    database.execute("DELETE FROM api_keys WHERE id=?", (rid,))
    flash("کلید حذف شد.", "success")
    return redirect(url_for("admin_api_keys"))


@app.route("/admin/api-docs")
@admin_required
def admin_api_docs():
    rows = database.query("SELECT * FROM api_keys WHERE is_active=1 ORDER BY id DESC")
    return render_template("admin/api_docs.html", keys=rows, page_title="مستندات API")


# ---------- مدیریت دسته‌بندی دوره‌ها ----------
@app.route("/admin/course-categories")
@admin_required
def admin_course_categories():
    rows = database.query(
        """SELECT cc.*, (SELECT COUNT(*) FROM courses c WHERE c.category_id=cc.id) AS course_count
           FROM course_categories cc ORDER BY cc.sort_order, cc.id""")
    return render_template("admin/course_categories.html", rows=rows,
                           page_title="دسته‌بندی دوره‌ها")


@app.route("/admin/course-categories/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_course_category_new():
    title = request.form.get("title", "").strip()
    if not title:
        flash("عنوان دسته الزامی است.", "error")
        return redirect(url_for("admin_course_categories"))
    slug = jdate.en_digits(request.form.get("slug", "").strip()) or \
        re.sub(r"\s+", "-", title.strip())[:40]
    mx = database.query("SELECT MAX(sort_order) m FROM course_categories", one=True)["m"] or 0
    database.execute(
        """INSERT OR IGNORE INTO course_categories (slug, title, icon, color, sort_order)
           VALUES (?,?,?,?,?)""",
        (slug, title, request.form.get("icon", "📘").strip() or "📘",
         request.form.get("color", "#15803d").strip() or "#15803d", mx + 1))
    flash("دسته جدید اضافه شد.", "success")
    return redirect(url_for("admin_course_categories"))


@app.route("/admin/course-categories/<int:rid>/edit", methods=["POST"])
@admin_required
@admin_csrf
def admin_course_category_edit(rid):
    database.execute(
        "UPDATE course_categories SET title=?, icon=?, color=?, sort_order=?, is_visible=? WHERE id=?",
        (request.form.get("title", "").strip(), request.form.get("icon", "📘").strip(),
         request.form.get("color", "#15803d").strip(),
         request.form.get("sort_order", 0, type=int),
         1 if request.form.get("is_visible") else 0, rid))
    flash("دسته به‌روزرسانی شد.", "success")
    return redirect(url_for("admin_course_categories"))


@app.route("/admin/course-categories/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_course_category_delete(rid):
    database.execute("UPDATE courses SET category_id=NULL WHERE category_id=?", (rid,))
    database.execute("DELETE FROM course_categories WHERE id=?", (rid,))
    flash("دسته حذف شد (دوره‌های آن دسته‌بندی خالی شدند).", "success")
    return redirect(url_for("admin_course_categories"))


# ---------- مدیریت انجمن‌ها ----------
@app.route("/admin/forum")
@admin_required
def admin_forum():
    cats = database.query(
        """SELECT fc.*,
             (SELECT COUNT(*) FROM forum_topics t WHERE t.category_id=fc.id) AS topics_count
           FROM forum_categories fc ORDER BY fc.sort_order, fc.id""")
    topics = database.query(
        """SELECT t.*, fc.title AS cat_title,
             (SELECT COUNT(*) FROM forum_posts p WHERE p.topic_id=t.id) AS posts
           FROM forum_topics t JOIN forum_categories fc ON fc.id=t.category_id
           ORDER BY t.id DESC LIMIT 200""")
    return render_template("admin/forum.html", cats=cats, topics=topics,
                           page_title="مدیریت انجمن‌ها")


@app.route("/admin/forum/categories/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_cat_new():
    title = request.form.get("title", "").strip()
    if not title:
        flash("عنوان انجمن الزامی است.", "error")
        return redirect(url_for("admin_forum"))
    slug = jdate.en_digits(request.form.get("slug", "").strip()) or \
        re.sub(r"\s+", "-", title.strip())[:40]
    mx = database.query("SELECT MAX(sort_order) m FROM forum_categories", one=True)["m"] or 0
    database.execute(
        """INSERT OR IGNORE INTO forum_categories (slug, title, description, icon, sort_order)
           VALUES (?,?,?,?,?)""",
        (slug, title, request.form.get("description", "").strip(),
         request.form.get("icon", "💬").strip() or "💬", mx + 1))
    flash("انجمن جدید اضافه شد.", "success")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/categories/<int:rid>/edit", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_cat_edit(rid):
    database.execute(
        "UPDATE forum_categories SET title=?, description=?, icon=?, sort_order=?, is_visible=? WHERE id=?",
        (request.form.get("title", "").strip(), request.form.get("description", "").strip(),
         request.form.get("icon", "💬").strip(), request.form.get("sort_order", 0, type=int),
         1 if request.form.get("is_visible") else 0, rid))
    flash("انجمن به‌روزرسانی شد.", "success")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/categories/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_cat_delete(rid):
    database.execute("DELETE FROM forum_categories WHERE id=?", (rid,))
    flash("انجمن و تمام تاپیک‌ها/پاسخ‌های آن حذف شد.", "success")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/topics/<int:rid>/toggle-pin", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_topic_pin(rid):
    database.execute(
        "UPDATE forum_topics SET is_pinned = 1 - is_pinned WHERE id=?", (rid,))
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/topics/<int:rid>/toggle-lock", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_topic_lock(rid):
    database.execute(
        "UPDATE forum_topics SET is_locked = 1 - is_locked WHERE id=?", (rid,))
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/topics/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_topic_delete(rid):
    database.execute("DELETE FROM forum_posts WHERE topic_id=?", (rid,))
    database.execute("DELETE FROM forum_topics WHERE id=?", (rid,))
    flash("تاپیک و پاسخ‌های آن حذف شد.", "success")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/posts/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_forum_post_delete(rid):
    database.execute("DELETE FROM forum_posts WHERE id=?", (rid,))
    flash("پاسخ حذف شد.", "success")
    return redirect(request.referrer or url_for("admin_forum"))


# ---------- مدیریت چت هوشمند ----------
@app.route("/admin/chat-docs")
@admin_required
def admin_chat_docs():
    rows = database.query(
        """SELECT * FROM chat_documents ORDER BY is_active DESC, priority DESC, id DESC""")
    total_hits = database.query(
        "SELECT COALESCE(SUM(hit_count),0) n FROM chat_documents", one=True)["n"]
    return render_template("admin/chat_docs.html", rows=rows, total_hits=total_hits,
                           page_title="مستندات چت هوشمند")


@app.route("/admin/chat-docs/new", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_chat_doc_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("عنوان و محتوای مستند الزامی است.", "error")
            return redirect(request.url)
        database.execute(
            """INSERT INTO chat_documents (title, content, keywords, link, link_label, category, priority, is_active)
               VALUES (?,?,?,?,?,?,?,?)""",
            (title, content, request.form.get("keywords", "").strip(),
             request.form.get("link", "").strip(), request.form.get("link_label", "").strip(),
             request.form.get("category", "عمومی").strip() or "عمومی",
             request.form.get("priority", 0, type=int),
             1 if request.form.get("is_active", "on") else 0))
        flash("مستند جدید به پایگاه دانش چت اضافه شد.", "success")
        return redirect(url_for("admin_chat_docs"))
    return render_template("admin/chat_doc_form.html", row=None, page_title="مستند جدید چت")


@app.route("/admin/chat-docs/<int:rid>", methods=["GET", "POST"])
@admin_required
@admin_csrf
def admin_chat_doc_edit(rid):
    row = database.query("SELECT * FROM chat_documents WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("عنوان و محتوای مستند الزامی است.", "error")
            return redirect(request.url)
        database.execute(
            """UPDATE chat_documents SET title=?, content=?, keywords=?, link=?, link_label=?,
               category=?, priority=?, is_active=? WHERE id=?""",
            (title, content, request.form.get("keywords", "").strip(),
             request.form.get("link", "").strip(), request.form.get("link_label", "").strip(),
             request.form.get("category", "عمومی").strip() or "عمومی",
             request.form.get("priority", 0, type=int),
             1 if request.form.get("is_active") else 0, rid))
        flash("مستند به‌روزرسانی شد.", "success")
        return redirect(url_for("admin_chat_docs"))
    return render_template("admin/chat_doc_form.html", row=row, page_title="ویرایش مستند چت")


@app.route("/admin/chat-docs/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_chat_doc_delete(rid):
    database.execute("DELETE FROM chat_documents WHERE id=?", (rid,))
    flash("مستند حذف شد.", "success")
    return redirect(url_for("admin_chat_docs"))


@app.route("/admin/chat-logs")
@admin_required
def admin_chat_logs():
    only_unanswered = request.args.get("unanswered") == "1"
    where = "WHERE is_answered=0" if only_unanswered else ""
    rows = database.query(
        f"SELECT * FROM chat_logs {where} ORDER BY id DESC LIMIT 300")
    stats = {
        "total": database.query("SELECT COUNT(*) n FROM chat_logs", one=True)["n"],
        "answered": database.query("SELECT COUNT(*) n FROM chat_logs WHERE is_answered=1", one=True)["n"],
        "unanswered": database.query("SELECT COUNT(*) n FROM chat_logs WHERE is_answered=0", one=True)["n"],
        "today": database.query(
            "SELECT COUNT(*) n FROM chat_logs WHERE created_at >= date('now','localtime')", one=True)["n"],
    }
    return render_template("admin/chat_logs.html", rows=rows, stats=stats,
                           only_unanswered=only_unanswered, page_title="گفتگوهای چت")


@app.route("/admin/chat-logs/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_chat_log_delete(rid):
    database.execute("DELETE FROM chat_logs WHERE id=?", (rid,))
    return redirect(request.referrer or url_for("admin_chat_logs"))


@app.route("/admin/chat-logs/clear", methods=["POST"])
@admin_required
@admin_csrf
def admin_chat_logs_clear():
    database.execute("DELETE FROM chat_logs")
    flash("تاریخچه گفتگوها پاک شد.", "success")
    return redirect(url_for("admin_chat_logs"))


# ---------- مدیریت اعضای هیئت مدیره ----------
BOARD_UPLOAD_EXT = {"png", "jpg", "jpeg", "webp"}


def _save_member_photo(file_storage, member_id):
    """ذخیره عکس عضو هیئت مدیره"""
    if not file_storage or not file_storage.filename:
        return ""
    filename = os.path.basename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in BOARD_UPLOAD_EXT:
        raise ValueError("عکس باید با فرمت PNG، JPG یا WEBP باشد")
    data = file_storage.read()
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("حجم عکس نباید بیشتر از ۲ مگابایت باشد")
    safe_name = f"board_{member_id}.{ext}"
    with open(os.path.join(app.config["UPLOAD_FOLDER"], safe_name), "wb") as fh:
        fh.write(data)
    return safe_name


@app.route("/admin/board")
@admin_required
def admin_board():
    rows = database.query("SELECT * FROM board_members ORDER BY sort_order, id")
    return render_template("admin/board.html", rows=rows, page_title="هیئت مدیره")


@app.route("/admin/board/new", methods=["POST"])
@admin_required
@admin_csrf
def admin_board_new():
    name = request.form.get("full_name", "").strip()
    if not name:
        flash("نام عضو الزامی است.", "error")
        return redirect(url_for("admin_board"))
    mx = database.query("SELECT MAX(sort_order) m FROM board_members", one=True)["m"] or 0
    mid = database.execute(
        """INSERT INTO board_members (full_name, role, bio, skills, sort_order, is_visible)
           VALUES (?,?,?,?,?,?)""",
        (name, request.form.get("role", "عضو هیئت مدیره").strip() or "عضو هیئت مدیره",
         request.form.get("bio", "").strip(), request.form.get("skills", "").strip(),
         request.form.get("sort_order", mx + 1, type=int),
         1 if request.form.get("is_visible", "on") else 0))
    try:
        photo = _save_member_photo(request.files.get("photo"), mid)
        if photo:
            database.execute("UPDATE board_members SET photo=? WHERE id=?", (photo, mid))
    except ValueError as err:
        flash(f"عضو ثبت شد اما عکس ذخیره نشد: {err}", "error")
    flash("عضو جدید اضافه شد.", "success")
    return redirect(url_for("admin_board"))


@app.route("/admin/board/<int:rid>/edit", methods=["POST"])
@admin_required
@admin_csrf
def admin_board_edit(rid):
    row = database.query("SELECT * FROM board_members WHERE id=?", (rid,), one=True)
    if not row:
        abort(404)
    database.execute(
        "UPDATE board_members SET full_name=?, role=?, bio=?, skills=?, sort_order=?, is_visible=? WHERE id=?",
        (request.form.get("full_name", "").strip(),
         request.form.get("role", "عضو هیئت مدیره").strip(),
         request.form.get("bio", "").strip(), request.form.get("skills", "").strip(),
         request.form.get("sort_order", row["sort_order"], type=int),
         1 if request.form.get("is_visible") else 0, rid))
    try:
        photo = _save_member_photo(request.files.get("photo"), rid)
        if photo:
            database.execute("UPDATE board_members SET photo=? WHERE id=?", (photo, rid))
    except ValueError as err:
        flash(f"اطلاعات ذخیره شد اما عکس ذخیره نشد: {err}", "error")
    flash("اطلاعات عضو به‌روزرسانی شد.", "success")
    return redirect(url_for("admin_board"))


@app.route("/admin/board/<int:rid>/delete", methods=["POST"])
@admin_required
@admin_csrf
def admin_board_delete(rid):
    row = database.query("SELECT * FROM board_members WHERE id=?", (rid,), one=True)
    if row and row["photo"]:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], row["photo"]))
        except OSError:
            pass
    database.execute("DELETE FROM board_members WHERE id=?", (rid,))
    flash("عضو حذف شد.", "success")
    return redirect(url_for("admin_board"))


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
# REST API v1 برای سامانه‌های خارجی (درخواست‌کنندگان مشاوره)
# احراز هویت: هدر X-API-Key یا Authorization: Bearer <key>
# ==================================================================
def _json_error(status, code, message):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def _authenticate_api_key():
    """اعتبارسنجی کلید API — در صورت موفقیت ردیف کلید برمی‌گردد"""
    key = request.headers.get("X-API-Key", "").strip()
    if not key:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
    if not key:
        return None, _json_error(401, "missing_api_key",
                                 "کلید API ارسال نشده است. آن را در هدر X-API-Key قرار دهید.")
    row = database.query("SELECT * FROM api_keys WHERE key=?", (key,), one=True)
    if not row:
        return None, _json_error(401, "invalid_api_key", "کلید API نامعتبر است.")
    if not row["is_active"]:
        return None, _json_error(403, "inactive_api_key", "این کلید API غیرفعال شده است.")
    database.execute(
        """UPDATE api_keys SET request_count=request_count+1,
           last_used_at=datetime('now','localtime') WHERE id=?""", (row["id"],))
    return row, None


@app.route("/api/v1/ping")
def api_v1_ping():
    key, err = _authenticate_api_key()
    if err:
        return err
    return jsonify({
        "ok": True,
        "service": "rosecenter-api",
        "version": "v1",
        "system": key["name"],
        "now": jdate.today_jalali_fa(),
    })


@app.route("/api/v1/consultations", methods=["POST"])
def api_v1_create_consultation():
    """ثبت درخواست مشاوره از سامانه خارجی"""
    key, err = _authenticate_api_key()
    if err:
        return err

    payload = request.get_json(silent=True) or request.form.to_dict()
    if not payload:
        return _json_error(400, "empty_body",
                           "بدنه درخواست خالی است. داده‌ها را به‌صورت JSON ارسال کنید.")

    def _field(*names):
        for n in names:
            v = payload.get(n)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    full_name = _field("full_name", "name", "fullName")
    phone = jdate.en_digits(_field("phone", "mobile", "tel"))
    service_type = _field("service_type", "serviceType", "service")

    if not full_name:
        return _json_error(400, "missing_full_name", "فیلد full_name الزامی است.")
    if not phone or not phone.isdigit() or not (10 <= len(phone) <= 11):
        return _json_error(400, "invalid_phone", "شماره تماس معتبر نیست (مثال: 09123456789).")
    if not service_type:
        return _json_error(400, "missing_service_type",
                           f"فیلد service_type الزامی است. مقادیر مجاز: {THERAPY_TYPES}")
    if service_type not in THERAPY_TYPES:
        return _json_error(400, "invalid_service_type",
                           f"service_type نامعتبر است. مقادیر مجاز: {THERAPY_TYPES}")

    code = gen_tracking_code("RC")
    booking_id = database.execute(
        """INSERT INTO bookings (tracking_code, full_name, phone, service_type, center, note,
                                 source, user_id, api_key_id)
           VALUES (?,?,?,?,?,?, 'API', NULL, ?)""",
        (code, full_name, phone, service_type,
         _field("center"), _field("note"), key["id"]))
    return jsonify({
        "ok": True,
        "message": "درخواست مشاوره با موفقیت ثبت شد.",
        "booking_id": booking_id,
        "tracking_code": code,
        "status": "در انتظار بررسی",
    }), 201


@app.route("/api/v1/consultations")
def api_v1_list_consultations():
    """فهرست درخواست‌های مشاوره (اختیاری: status، limit، offset)"""
    key, err = _authenticate_api_key()
    if err:
        return err
    status = request.args.get("status", "").strip()
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)
    where, args = "WHERE 1=1", []
    if status:
        where += " AND status=?"
        args.append(status)
    total = database.query(
        f"SELECT COUNT(*) n FROM bookings {where}", args, one=True)["n"]
    rows = database.query(
        f"""SELECT tracking_code, full_name, phone, service_type, center, note, status,
                   source, created_at
            FROM bookings {where} ORDER BY id DESC LIMIT ? OFFSET ?""",
        (*args, limit, offset))
    return jsonify({
        "ok": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(r) for r in rows],
    })


@app.route("/api/v1/consultations/<tracking_code>")
def api_v1_get_consultation(tracking_code):
    """استعلام وضعیت یک درخواست با کد پیگیری"""
    key, err = _authenticate_api_key()
    if err:
        return err
    row = database.query(
        """SELECT tracking_code, full_name, phone, service_type, center, note, status,
                  admin_note, source, created_at
           FROM bookings WHERE tracking_code=?""",
        (tracking_code.strip().upper(),), one=True)
    if not row:
        return _json_error(404, "not_found", "درخواستی با این کد پیگیری یافت نشد.")
    return jsonify({"ok": True, "item": dict(row)})


@app.route("/api/v1/meta/services")
def api_v1_meta_services():
    """فهرست نوع‌های درمان مجاز + مراکز فعال (برای سامانه‌های خارجی)"""
    key, err = _authenticate_api_key()
    if err:
        return err
    centers = database.query(
        "SELECT province FROM centers WHERE is_soon=0 ORDER BY sort_order")
    return jsonify({
        "ok": True,
        "service_types": THERAPY_TYPES,
        "statuses": REQUEST_STATUSES,
        "centers": [r["province"] for r in centers],
    })


# ==================================================================
# خطاها و API
# ==================================================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": {"code": "not_found", "message": "مسیر یافت نشد."}}), 404
    return render_template("404.html", page_title="صفحه یافت نشد"), 404


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "rosecenter-flask"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
