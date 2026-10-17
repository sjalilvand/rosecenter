"""روت‌های عمومی سایت"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from ..db import query, execute
from ..utils import (gen_tracking_code, THERAPY_TYPES, CONSULT_TYPES,
                     TIME_SLOTS, FEEDBACK_KINDS)

bp = Blueprint('main', __name__)


# ---------------- صفحه اصلی ----------------
@bp.route('/')
def home():
    services = query("SELECT * FROM services WHERE is_active=1 ORDER BY sort_order, id")
    therapy = [s for s in services if s['category'] == 'روان درمانی']
    counseling = [s for s in services if s['category'] == 'مشاوره']
    education = [s for s in services if s['category'] == 'آموزش']
    others = [s for s in services if s['category'] == 'سایر خدمات']
    testimonials = query(
        "SELECT * FROM testimonials WHERE is_active=1 ORDER BY sort_order, id LIMIT 6")
    faqs = query("SELECT * FROM faqs WHERE is_active=1 ORDER BY sort_order, id LIMIT 6")
    news = query(
        "SELECT * FROM news WHERE is_published=1 ORDER BY created_at DESC, id DESC LIMIT 3")
    return render_template('index.html',
                           therapy=therapy, counseling=counseling,
                           education=education, others=others,
                           testimonials=testimonials, faqs=faqs, news=news)


# ---------------- خدمات ----------------
@bp.route('/services')
def services():
    services = query("SELECT * FROM services WHERE is_active=1 ORDER BY sort_order, id")
    grouped = {}
    for s in services:
        grouped.setdefault(s['category'], []).append(s)
    return render_template('services.html', grouped=grouped)


@bp.route('/services/<slug>')
def service_detail(slug):
    service = query("SELECT * FROM services WHERE slug=? AND is_active=1", (slug,), one=True)
    if not service:
        abort(404)
    related = query(
        "SELECT * FROM services WHERE category=? AND slug<>? AND is_active=1 ORDER BY sort_order LIMIT 4",
        (service['category'], slug))
    return render_template('service_detail.html', service=service, related=related)


# ---------------- مراکز استانی ----------------
@bp.route('/centers')
def centers():
    rows = query("SELECT * FROM centers WHERE is_active=1 ORDER BY sort_order, id")
    grouped = {}
    for c in rows:
        grouped.setdefault(c['province'], []).append(c)
    return render_template('centers.html', grouped=grouped)


# ---------------- درخواست همکاری ----------------
@bp.route('/cooperation', methods=['GET', 'POST'])
def cooperation():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        if not full_name or not phone:
            flash('نام و شماره تماس الزامی است.', 'error')
            return redirect(url_for('main.cooperation'))
        code = gen_tracking_code('cooperation')
        execute(
            """INSERT INTO cooperation_requests
               (tracking_code, full_name, phone, email, education, field, message)
               VALUES (?,?,?,?,?,?,?)""",
            (code, full_name, phone,
             request.form.get('email', '').strip(),
             request.form.get('education', '').strip(),
             request.form.get('field', '').strip(),
             request.form.get('message', '').strip()))
        return render_template('success.html',
                               code=code,
                               title='درخواست همکاری شما ثبت شد',
                               desc='کارشناسان ما پس از بررسی رزومه شما، از طریق شماره تماس اعلام شده با شما در ارتباط خواهند بود.')
    return render_template('cooperation.html')


# ---------------- آکادمی رز (دوره‌های آموزشی) ----------------
@bp.route('/academy')
def academy():
    courses = query("SELECT * FROM courses WHERE is_active=1 ORDER BY created_at DESC, id DESC")
    return render_template('academy.html', courses=courses)


@bp.route('/academy/<slug>', methods=['GET', 'POST'])
def course_detail(slug):
    course = query("SELECT * FROM courses WHERE slug=? AND is_active=1", (slug,), one=True)
    if not course:
        abort(404)
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        if not full_name or not phone:
            flash('نام و شماره تماس الزامی است.', 'error')
            return redirect(url_for('main.course_detail', slug=slug))
        code = gen_tracking_code('course')
        execute(
            """INSERT INTO course_registrations
               (tracking_code, course_id, full_name, phone, email)
               VALUES (?,?,?,?,?)""",
            (code, course['id'], full_name, phone,
             request.form.get('email', '').strip()))
        return render_template('success.html',
                               code=code,
                               title='ثبت‌نام شما در دوره انجام شد',
                               desc=f"درخواست ثبت‌نام شما در دوره «{course['title']}» ثبت شد. همکاران ما برای تکمیل فرآیند ثبت‌نام با شما تماس خواهند گرفت.")
    return render_template('course_detail.html', course=course)


# ---------------- اخبار و اطلاعیه‌ها ----------------
@bp.route('/news')
def news():
    items = query("SELECT * FROM news WHERE is_published=1 ORDER BY created_at DESC, id DESC")
    return render_template('news.html', items=items)


@bp.route('/news/<slug>')
def news_detail(slug):
    item = query("SELECT * FROM news WHERE slug=? AND is_published=1", (slug,), one=True)
    if not item:
        abort(404)
    latest = query(
        "SELECT * FROM news WHERE slug<>? AND is_published=1 ORDER BY created_at DESC LIMIT 4",
        (slug,))
    return render_template('news_detail.html', item=item, latest=latest)


# ---------------- درباره ما ----------------
@bp.route('/about')
def about():
    return render_template('about.html')


# ---------------- تماس با ما ----------------
@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not message:
            flash('نام و متن پیام الزامی است.', 'error')
            return redirect(url_for('main.contact'))
        execute(
            "INSERT INTO contact_messages (name, email, phone, subject, message) VALUES (?,?,?,?,?)",
            (name, request.form.get('email', '').strip(),
             request.form.get('phone', '').strip(),
             request.form.get('subject', '').strip(), message))
        flash('پیام شما با موفقیت ارسال شد. به‌زودی با شما تماس می‌گیریم.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')


# ---------------- درخواست مشاوره ----------------
@bp.route('/consultation', methods=['GET', 'POST'])
def consultation():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        description = request.form.get('description', '').strip()
        if not full_name or not phone or not description:
            flash('تکمیل نام، شماره تماس و توضیحات الزامی است.', 'error')
            return redirect(url_for('main.consultation'))
        code = gen_tracking_code('consultation')
        execute(
            """INSERT INTO consultations
               (tracking_code, service_type, full_name, phone, email, subject, description)
               VALUES (?,?,?,?,?,?,?)""",
            (code,
             request.form.get('service_type', 'مشاوره فردی').strip(),
             full_name, phone,
             request.form.get('email', '').strip(),
             request.form.get('subject', '').strip(),
             description))
        return render_template('success.html',
                               code=code,
                               title='درخواست مشاوره شما ثبت شد',
                               desc='همکاران ما در اولین فرصت (حداکثر ۲۴ ساعت کاری) برای هماهنگی جلسه مشاوره با شما تماس خواهند گرفت.')
    return render_template('consultation.html', consult_types=CONSULT_TYPES)


# ---------------- رزرو نوبت آنلاین ----------------
@bp.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        preferred_date = request.form.get('preferred_date', '').strip()
        preferred_time = request.form.get('preferred_time', '').strip()
        if not full_name or not phone or not preferred_date or not preferred_time:
            flash('تکمیل همه فیلدهای ستاره‌دار الزامی است.', 'error')
            return redirect(url_for('main.appointment'))
        code = gen_tracking_code('appointment')
        execute(
            """INSERT INTO appointments
               (tracking_code, service_type, full_name, phone, email, preferred_date, preferred_time, note)
               VALUES (?,?,?,?,?,?,?,?)""",
            (code,
             request.form.get('service_type', 'درمان فردی').strip(),
             full_name, phone,
             request.form.get('email', '').strip(),
             preferred_date, preferred_time,
             request.form.get('note', '').strip()))
        return render_template('success.html',
                               code=code,
                               title='نوبت شما با موفقیت ثبت شد',
                               desc='نوبت شما پس از تأیید کارشناسان، از طریق تماس یا پیامک به شما اطلاع داده خواهد شد.')
    return render_template('appointment.html',
                           therapy_types=THERAPY_TYPES, time_slots=TIME_SLOTS)


# ---------------- پیگیری درخواست ----------------
TRACK_TABLES = [
    ('appointments', 'نوبت‌دهی آنلاین'),
    ('consultations', 'درخواست مشاوره'),
    ('cooperation_requests', 'درخواست همکاری'),
    ('feedbacks', 'پیشنهاد و انتقاد'),
    ('course_registrations', 'ثبت‌نام دوره'),
]


@bp.route('/tracking', methods=['GET'])
def tracking():
    code = request.args.get('code', '').strip().upper()
    result = None
    if code:
        for table, label in TRACK_TABLES:
            row = query(f"SELECT * FROM {table} WHERE tracking_code=?", (code,), one=True)
            if row:
                result = {'row': row, 'type': label, 'table': table}
                break
        if not result:
            flash('هیچ درخواستی با این شماره پیگیری یافت نشد. لطفاً کد را بررسی کنید.', 'error')
    return render_template('tracking.html', code=code, result=result)


# ---------------- پیشنهاد و انتقاد ----------------
@bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash('متن پیام الزامی است.', 'error')
            return redirect(url_for('main.feedback'))
        code = gen_tracking_code('feedback')
        execute(
            """INSERT INTO feedbacks
               (tracking_code, kind, name, email, phone, subject, message)
               VALUES (?,?,?,?,?,?,?)""",
            (code,
             request.form.get('kind', 'پیشنهاد').strip(),
             request.form.get('name', '').strip(),
             request.form.get('email', '').strip(),
             request.form.get('phone', '').strip(),
             request.form.get('subject', '').strip(),
             message))
        return render_template('success.html',
                               code=code,
                               title='پیام شما ثبت شد',
                               desc='از اینکه با ما همراه هستید سپاسگزاریم. پیام شما توسط واحد نظارت بررسی خواهد شد.')
    return render_template('feedback.html', feedback_kinds=FEEDBACK_KINDS)


# ---------------- سوالات متداول ----------------
@bp.route('/faq')
def faq():
    faqs = query("SELECT * FROM faqs WHERE is_active=1 ORDER BY sort_order, id")
    grouped = {}
    for f in faqs:
        grouped.setdefault(f['category'] or 'عمومی', []).append(f)
    return render_template('faq.html', grouped=grouped)


# ---------------- جستجو ----------------
@bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    services = news = courses = []
    if q:
        like = f"%{q}%"
        services = query(
            "SELECT * FROM services WHERE is_active=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",
            (like, like, like))
        news = query(
            "SELECT * FROM news WHERE is_published=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",
            (like, like, like))
        courses = query(
            "SELECT * FROM courses WHERE is_active=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",
            (like, like, like))
    return render_template('search.html', q=q, services=services,
                           news=news, courses=courses)
