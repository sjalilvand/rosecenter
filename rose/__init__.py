"""پکیج اصلی برنامه - کارخانه ساخت اپلیکیشن فلسک"""
import os
from datetime import datetime
from flask import Flask

from .db import close_db, query
from .utils import status_label, STATUS_MAP, STATUS_CLASS, jdate, fa_num


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rose-center-change-me-in-production')
    app.config['DATABASE'] = os.environ.get(
        'DATABASE', os.path.join(base_dir, 'rosecenter.db'))
    app.config['JSON_AS_ASCII'] = False
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

    # بستن اتصال دیتابیس در پایان هر درخواست
    app.teardown_appcontext(close_db)

    # ثبت Blueprint ها
    from .routes.main import bp as main_bp
    from .routes.admin import bp as admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # فیلترها و متغیرهای سراسری قالب‌ها
    @app.template_filter('status_label')
    def _status_label(s):
        return status_label(s)

    @app.template_filter('jdate')
    def _jdate(v, with_time=False):
        return jdate(v, with_time)

    @app.template_filter('fa_num')
    def _fa_num(v):
        return fa_num(v)

    @app.context_processor
    def inject_globals():
        try:
            rows = query("SELECT key, value FROM settings")
            settings = {r['key']: r['value'] for r in rows}
        except Exception:
            settings = {}
        return dict(
            settings=settings,
            STATUS_MAP=STATUS_MAP,
            STATUS_CLASS=STATUS_CLASS,
            now_year=datetime.now().year,
            today=datetime.now().strftime('%Y-%m-%d'),
        )

    # صفحات خطا
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('500.html'), 500

    return app
