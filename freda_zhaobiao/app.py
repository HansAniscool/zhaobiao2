import os
from flask import Flask, request, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_caching import Cache
from flask_wtf import CSRFProtect
from datetime import timedelta
from app.middleware.error_handlers import register_error_handlers, monitor_performance, handle_errors, APIResponse
from app.middleware.security import register_security_headers, rate_limit, api_rate_limit, sanitize_params, require_content_type
from app.utils.cache import cache_manager
from app.services.logger_service import logger_service
from app.models import User, Tender, CrawlerTask, Favorite, SearchHistory, SystemLog, CrawlHistory, GovernmentWebsite

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("data/tender.db")}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('exports', exist_ok=True)

from app.extensions import db, login_manager, cache, csrf

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
cache.init_app(app, config={'CACHE_TYPE': 'simple'})
csrf.init_app(app)

register_error_handlers(app)
register_security_headers(app)
monitor_performance(app)

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

@app.context_processor
def inject_globals():
    return {
        'app_name': '招标信息收集系统',
        'app_version': '1.0.0',
        'current_year': __import__('datetime').datetime.now().year
    }

@app.before_request
def before_request():
    g.user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
    if request.is_json:
        sanitize_params(lambda: None)()

from app.models import User, Tender, CrawlerTask, Favorite, SearchHistory, SystemLog, CrawlHistory, GovernmentWebsite
from app.routes import auth, tenders, crawler, admin, api

app.register_blueprint(auth.bp, url_prefix='/auth')
app.register_blueprint(tenders.bp)
app.register_blueprint(crawler.bp, url_prefix='/crawler')
app.register_blueprint(admin.bp, url_prefix='/admin')
app.register_blueprint(api.bp, url_prefix='/api')

@app.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': 'ok'
        })
    except Exception as e:
        logger_service.error(f"Health check failed: {str(e)}", module='health')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    return APIResponse.success({
        'stats': cache_manager.get_stats(),
        'performance': __import__('middleware.error_handlers', fromlist=['performance_monitor']).performance_monitor.get_stats()
    })

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': {
            'message': '页面不存在',
            'code': 'NOT_FOUND'
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger_service.error(f"Internal server error: {str(error)}", module='app')
    return jsonify({
        'success': False,
        'error': {
            'message': '服务器内部错误',
            'code': 'INTERNAL_ERROR'
        }
    }), 500

with app.app_context():
    db.create_all()
    
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        logger_service.info('Default admin account created: admin / admin123', module='init')
        print('默认管理员账号已创建: admin / admin123')

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger_service.info(f'Starting application on port {port}', module='app')
    
    print(f'应用已启动: http://0.0.0.0:{port}')
    print('按 Ctrl+C 停止服务')
    
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
