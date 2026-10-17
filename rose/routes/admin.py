"""پنل مدیریت - احراز هویت، داشبورد، CRUD عمومی، تنظیمات"""
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, abort)

from werkzeug.security import check_password_hash, generate_password_hash

from ..db import query, execute, count
from ..utils import STATUS_MAP

bp = Blueprint('admin', __name__)


# ==================== احراز هویت ====================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return wrapper


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = query("SELECT * FROM users WHERE username=?", (username,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session['admin_id'] = user['id']
            session['admin_name'] = user['full_name'] or user['username']
            return redirect(url_for('admin.dashboard'))
        flash('نام کاربری یا رمز عبور اشتباه است.', 'error')
    return render_template('admin/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        user = query("SELECT * FROM users WHERE id=?", (session['admin_id'],), one=True)
        if not user or not check_password_hash(user['password_hash'], current):
            flash('رمز عبور فعلی اشتباه است.', 'error')
        elif len(new) < 6:
            flash('رمز عبور جدید باید حداقل ۶ کاراکتر باشد.', 'error')
        elif new != confirm:
            flash('تکرار رمز عبور مطابقت ندارد.', 'error')
        else:
            execute("UPDATE users SET password_hash=? WHERE id=?",
                    (generate_password_hash(new), user['id']))
            flash('رمز عبور با موفقیت تغییر کرد.', 'success')
            return redirect(url_for('admin.dashboard'))
    return render_template('admin/password.html')


# ==================== تعریف موجودیت‌ها (CRUD عمومی) ====================
E = dict  # خوانایی بیشتر

ENTITIES = {
    # ---------- محتوا ----------
    'services': E(
        title='خدمات', icon='🧩', table='services', creatable=True,
        order='sort_order, id',
        list_fields=[('title', 'عنوان'), ('category', 'دسته'),
                     ('sort_order', 'ترتیب'), ('is_active', 'فعال')],
        fields=[
            E(name='title', label='عنوان', type='text', required=True),
            E(name='slug', label='نامک لاتین (در آدرس صفحه)', type='text', required=True),
            E(name='category', label='دسته', type='select', required=True,
              options=['روان درمانی', 'مشاوره', 'آموزش', 'سایر خدمات']),
            E(name='icon', label='آیکون (ایموجی)', type='text', required=False),
            E(name='summary', label='خلاصه', type='textarea', required=False),
            E(name='content', label='متن کامل (پاراگراف‌ها را با دو اینتر جدا کنید)',
              type='textarea', required=False),
            E(name='features', label='ویژگی‌ها (هر خط یک مورد)', type='textarea', required=False),
            E(name='sort_order', label='ترتیب نمایش', type='number', required=False),
            E(name='is_active', label='فعال باشد', type='checkbox'),
        ]),
    'news': E(
        title='اخبار و اطلاعیه‌ها', icon='📰', table='news', creatable=True,
        order='id DESC',
        list_fields=[('title', 'عنوان'), ('created_at', 'تاریخ'),
                     ('is_published', 'منتشر شده')],
        fields=[
            E(name='title', label='عنوان', type='text', required=True),
            E(name='slug', label='نامک لاتین', type='text', required=True),
            E(name='summary', label='خلاصه', type='textarea', required=False),
            E(name='content', label='متن خبر', type='textarea', required=False),
            E(name='is_published', label='منتشر شده باشد', type='checkbox'),
        ]),
    'courses': E(
        title='دوره‌های آکادمی رز', icon='🎓', table='courses', creatable=True,
        order='id DESC',
        list_fields=[('title', 'عنوان'), ('level', 'سطح'), ('teacher', 'مدرس'),
                     ('start_date', 'شروع'), ('is_active', 'فعال')],
        fields=[
            E(name='title', label='عنوان دوره', type='text', required=True),
            E(name='slug', label='نامک لاتین', type='text', required=True),
            E(name='level', label='سطح', type='select', required=True,
              options=['عمومی', 'تخصصی']),
            E(name='teacher', label='مدرس', type='text', required=False),
            E(name='summary', label='خلاصه', type='textarea', required=False),
            E(name='content', label='توضیحات کامل', type='textarea', required=False),
            E(name='duration', label='مدت دوره', type='text', required=False),
            E(name='price', label='شهریه', type='text', required=False),
            E(name='start_date', label='تاریخ شروع', type='text', required=False),
            E(name='capacity', label='ظرفیت', type='number', required=False),
            E(name='is_active', label='فعال باشد', type='checkbox'),
        ]),
    'centers': E(
        title='مراکز استانی', icon='🏢', table='centers', creatable=True,
        order='sort_order, id',
        list_fields=[('name', 'نام مرکز'), ('province', 'استان'),
                     ('phone', 'تلفن'), ('is_active', 'فعال')],
        fields=[
            E(name='name', label='نام مرکز', type='text', required=True),
            E(name='province', label='استان', type='text', required=True),
            E(name='city', label='شهر', type='text', required=False),
            E(name='address', label='آدرس', type='textarea', required=False),
            E(name='phone', label='تلفن', type='text', required=False),
            E(name='sort_order', label='ترتیب نمایش', type='number', required=False),
            E(name='is_active', label='فعال باشد', type='checkbox'),
        ]),
    'testimonials': E(
        title='نظرات مراجعین', icon='💬', table='testimonials', creatable=True,
        order='sort_order, id',
        list_fields=[('name', 'نام'), ('category', 'موضوع'), ('is_active', 'فعال')],
        fields=[
            E(name='name', label='نام', type='text', required=True),
            E(name='category', label='موضوع رضایت', type='text', required=False),
            E(name='text', label='متن نظر', type='textarea', required=True),
            E(name='sort_order', label='ترتیب نمایش', type='number', required=False),
            E(name='is_active', label='فعال باشد', type='checkbox'),
        ]),
    'faqs': E(
        title='سوالات متداول', icon='❓', table='faqs', creatable=True,
        order='sort_order, id',
        list_fields=[('question', 'سوال'), ('category', 'دسته'), ('is_active', 'فعال')],
        fields=[
            E(name='question', label='سوال', type='text', required=True),
            E(name='answer', label='پاسخ', type='textarea', required=True),
            E(name='category', label='دسته', type='select', required=True,
              options=['روان درمانی', 'مشاوره', 'نظارت و پشتیبانی', 'عمومی']),
            E(name='sort_order', label='ترتیب نمایش', type='number', required=False),
            E(name='is_active', label='فعال باشد', type='checkbox'),
        ]),

    # ---------- درخواست‌ها (بدون ایجاد از پنل) ----------
    'consultations': E(
        title='درخواست‌های مشاوره', icon='📝', table='consultations', creatable=False,
        order='id DESC', has_status=True,
        list_fields=[('tracking_code', 'کد پیگیری'), ('full_name', 'نام'),
                     ('service_type', 'نوع مشاوره'), ('phone', 'تلفن'),
                     ('status', 'وضعیت')],
        fields=[
            E(name='tracking_code', label='کد پیگیری', type='text', required=True),
            E(name='service_type', label='نوع مشاوره', type='text', required=True),
            E(name='full_name', label='نام', type='text', required=True),
            E(name='phone', label='تلفن', type='text', required=True),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='subject', label='موضوع', type='text', required=False),
            E(name='description', label='توضیحات', type='textarea', required=False),
            E(name='status', label='وضعیت', type='select', required=True,
              options=list(STATUS_MAP.keys()), option_labels=STATUS_MAP),
        ]),
    'appointments': E(
        title='نوبت‌های رزرو شده', icon='📅', table='appointments', creatable=False,
        order='id DESC', has_status=True,
        list_fields=[('tracking_code', 'کد پیگیری'), ('full_name', 'نام'),
                     ('service_type', 'نوع درمان'), ('preferred_date', 'تاریخ'),
                     ('preferred_time', 'ساعت'), ('status', 'وضعیت')],
        fields=[
            E(name='tracking_code', label='کد پیگیری', type='text', required=True),
            E(name='service_type', label='نوع درمان', type='text', required=True),
            E(name='full_name', label='نام', type='text', required=True),
            E(name='phone', label='تلفن', type='text', required=True),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='preferred_date', label='تاریخ (میلادی YYYY-MM-DD)', type='text', required=True),
            E(name='preferred_time', label='ساعت', type='text', required=True),
            E(name='note', label='توضیحات', type='textarea', required=False),
            E(name='status', label='وضعیت', type='select', required=True,
              options=list(STATUS_MAP.keys()), option_labels=STATUS_MAP),
        ]),
    'course_registrations': E(
        title='ثبت‌نام دوره‌ها', icon='🗂', table='course_registrations', creatable=False,
        order='id DESC', has_status=True,
        list_fields=[('tracking_code', 'کد پیگیری'), ('full_name', 'نام'),
                     ('phone', 'تلفن'), ('status', 'وضعیت')],
        fields=[
            E(name='tracking_code', label='کد پیگیری', type='text', required=True),
            E(name='course_id', label='شناسه دوره', type='number', required=True),
            E(name='full_name', label='نام', type='text', required=True),
            E(name='phone', label='تلفن', type='text', required=True),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='status', label='وضعیت', type='select', required=True,
              options=list(STATUS_MAP.keys()), option_labels=STATUS_MAP),
        ]),
    'cooperation_requests': E(
        title='درخواست‌های همکاری', icon='🤝', table='cooperation_requests',
        creatable=False, order='id DESC', has_status=True,
        list_fields=[('tracking_code', 'کد پیگیری'), ('full_name', 'نام'),
                     ('field', 'زمینه'), ('status', 'وضعیت')],
        fields=[
            E(name='tracking_code', label='کد پیگیری', type='text', required=True),
            E(name='full_name', label='نام', type='text', required=True),
            E(name='phone', label='تلفن', type='text', required=True),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='education', label='تحصیلات', type='text', required=False),
            E(name='field', label='زمینه تخصصی', type='text', required=False),
            E(name='message', label='پیام', type='textarea', required=False),
            E(name='status', label='وضعیت', type='select', required=True,
              options=list(STATUS_MAP.keys()), option_labels=STATUS_MAP),
        ]),
    'feedbacks': E(
        title='پیشنهاد و انتقاد', icon='📮', table='feedbacks',
        creatable=False, order='id DESC', has_status=True,
        list_fields=[('tracking_code', 'کد پیگیری'), ('kind', 'نوع'),
                     ('name', 'نام'), ('status', 'وضعیت')],
        fields=[
            E(name='tracking_code', label='کد پیگیری', type='text', required=True),
            E(name='kind', label='نوع', type='select', required=True,
              options=['پیشنهاد', 'انتقاد', 'گزارش مشکل']),
            E(name='name', label='نام', type='text', required=False),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='phone', label='تلفن', type='text', required=False),
            E(name='subject', label='موضوع', type='text', required=False),
            E(name='message', label='متن پیام', type='textarea', required=True),
            E(name='status', label='وضعیت', type='select', required=True,
              options=list(STATUS_MAP.keys()), option_labels=STATUS_MAP),
        ]),
    'contact_messages': E(
        title='پیام‌های تماس با ما', icon='📨', table='contact_messages',
        creatable=False, order='id DESC',
        list_fields=[('name', 'نام'), ('subject', 'موضوع'),
                     ('is_read', 'خوانده شده'), ('created_at', 'تاریخ')],
        fields=[
            E(name='name', label='نام', type='text', required=True),
            E(name='email', label='ایمیل', type='text', required=False),
            E(name='phone', label='تلفن', type='text', required=False),
            E(name='subject', label='موضوع', type='text', required=False),
            E(name='message', label='متن پیام', type='textarea', required=True),
            E(name='is_read', label='خوانده شده', type='checkbox'),
        ]),
}


def _entity(key):
    ent = ENTITIES.get(key)
    if not ent:
        abort(404)
    return ent


def _field_value(field, form):
    raw = form.get(field['name'], '')
    t = field['type']
    if t == 'checkbox':
        return 1 if form.get(field['name']) else 0
    if t == 'number':
        raw = raw.strip()
        return int(raw) if raw.isdigit() else 0
    return raw.strip()


# ==================== داشبورد ====================
@bp.route('/')
@login_required
def dashboard():
    stats = [
        ('درخواست مشاوره', count('consultations'), '📝', 'consultations'),
        ('نوبت‌های رزرو شده', count('appointments'), '📅', 'appointments'),
        ('درخواست همکاری', count('cooperation_requests'), '🤝', 'cooperation_requests'),
        ('ثبت‌نام دوره‌ها', count('course_registrations'), '🗂', 'course_registrations'),
        ('پیشنهاد و انتقاد', count('feedbacks'), '📮', 'feedbacks'),
        ('پیام‌های جدید', count('contact_messages', 'is_read=0'), '📨', 'contact_messages'),
        ('خدمات فعال', count('services', 'is_active=1'), '🧩', 'services'),
        ('اخبار منتشر شده', count('news', 'is_published=1'), '📰', 'news'),
    ]
    latest_consultations = query("SELECT * FROM consultations ORDER BY id DESC LIMIT 6")
    latest_appointments = query("SELECT * FROM appointments ORDER BY id DESC LIMIT 6")
    return render_template('admin/dashboard.html', stats=stats,
                           latest_consultations=latest_consultations,
                           latest_appointments=latest_appointments)


# ==================== CRUD عمومی ====================
@bp.route('/e/<key>')
@login_required
def entity_list(key):
    ent = _entity(key)
    status = request.args.get('status', '').strip()
    where, params = '1=1', []
    if status and ent.get('has_status'):
        where, params = 'status=?', [status]
    rows = query(f"SELECT * FROM {ent['table']} WHERE {where} ORDER BY {ent['order']} LIMIT 300",
                 tuple(params))
    return render_template('admin/generic_list.html', key=key, ent=ent,
                           rows=rows, status=status, STATUS_MAP=STATUS_MAP)


@bp.route('/e/<key>/new', methods=['GET', 'POST'])
@login_required
def entity_new(key):
    ent = _entity(key)
    if not ent.get('creatable'):
        abort(404)
    if request.method == 'POST':
        data = {f['name']: _field_value(f, request.form) for f in ent['fields']}
        cols = ', '.join(data.keys())
        qs = ', '.join(['?'] * len(data))
        try:
            execute(f"INSERT INTO {ent['table']} ({cols}) VALUES ({qs})",
                    tuple(data.values()))
            flash(f"«{ent['title']}» جدید با موفقیت اضافه شد.", 'success')
            return redirect(url_for('admin.entity_list', key=key))
        except Exception as exc:
            flash(f'خطا در ذخیره‌سازی (احتمالاً نامک تکراری است): {exc}', 'error')
    return render_template('admin/generic_form.html', key=key, ent=ent, item=None)


@bp.route('/e/<key>/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def entity_edit(key, item_id):
    ent = _entity(key)
    item = query(f"SELECT * FROM {ent['table']} WHERE id=?", (item_id,), one=True)
    if not item:
        abort(404)
    if request.method == 'POST':
        data = {f['name']: _field_value(f, request.form) for f in ent['fields']}
        sets = ', '.join(f"{k}=?" for k in data)
        try:
            execute(f"UPDATE {ent['table']} SET {sets} WHERE id=?",
                    (*data.values(), item_id))
            flash('تغییرات با موفقیت ذخیره شد.', 'success')
            return redirect(url_for('admin.entity_list', key=key))
        except Exception as exc:
            flash(f'خطا در ذخیره‌سازی: {exc}', 'error')
    return render_template('admin/generic_form.html', key=key, ent=ent, item=item)


@bp.route('/e/<key>/delete/<int:item_id>', methods=['POST'])
@login_required
def entity_delete(key, item_id):
    ent = _entity(key)
    execute(f"DELETE FROM {ent['table']} WHERE id=?", (item_id,))
    flash('مورد انتخاب‌شده حذف شد.', 'success')
    return redirect(url_for('admin.entity_list', key=key))


# ==================== تنظیمات ====================
SETTINGS_KEYS = [
    ('site_name', 'نام سایت'),
    ('tagline', 'شعار زیر نام سایت'),
    ('address', 'آدرس'),
    ('phone1', 'تلفن ۱'),
    ('phone2', 'تلفن ۲'),
    ('email', 'ایمیل'),
    ('working_hours', 'ساعات کاری'),
    ('instagram', 'اینستاگرام (آدرس)'),
    ('telegram', 'تلگرام (آدرس)'),
    ('whatsapp', 'واتساپ (شماره)'),
    ('footer_text', 'متن کوتاه فوتر'),
]


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        for k, _label in SETTINGS_KEYS:
            v = request.form.get(k, '').strip()
            if query("SELECT key FROM settings WHERE key=?", (k,), one=True):
                execute("UPDATE settings SET value=? WHERE key=?", (v, k))
            else:
                execute("INSERT INTO settings (key, value) VALUES (?,?)", (k, v))
        flash('تنظیمات ذخیره شد.', 'success')
        return redirect(url_for('admin.settings'))
    current = {r['key']: r['value'] for r in query("SELECT key, value FROM settings")}
    return render_template('admin/settings.html',
                           settings_keys=SETTINGS_KEYS, current=current)
