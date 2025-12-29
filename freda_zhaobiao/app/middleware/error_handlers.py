from flask import jsonify, request, render_template, g
from werkzeug.exceptions import HTTPException
from functools import wraps
import time
import traceback
from ..services.logger_service import logger_service

class AppException(Exception):
    def __init__(self, message, status_code=400, error_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        return {
            'error': {
                'message': self.message,
                'code': self.error_code,
                'details': self.details
            }
        }

def handle_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppException as e:
            logger_service.warning(
                f"Application error: {e.message}",
                module='error_handler',
                user_id=getattr(g, 'user_id', None)
            )
            if request.is_json or request.path.startswith('/api'):
                return jsonify(e.to_dict()), e.status_code
            return render_template('error.html', error=e), e.status_code
        except HTTPException as e:
            logger_service.info(
                f"HTTP error: {e.name} - {e.code}",
                module='error_handler'
            )
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': e.name, 'code': e.code}), e.code
            return render_template('error.html', error={'message': e.name, 'status_code': e.code}), e.code
        except Exception as e:
            tb = traceback.format_exc()
            logger_service.error(
                f"Unexpected error: {str(e)}",
                module='error_handler',
                traceback=tb,
                user_id=getattr(g, 'user_id', None)
            )
            if request.is_json or request.path.startswith('/api'):
                return jsonify({
                    'error': '服务器内部错误',
                    'code': 'INTERNAL_ERROR',
                    'message': str(e) if request.environ.get('DEBUG') else '请联系管理员'
                }), 500
            return render_template('error.html', error={'message': '服务器内部错误', 'status_code': 500}), 500
    return decorated

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': '请求无效', 'code': 'BAD_REQUEST'}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': '请先登录', 'code': 'UNAUTHORIZED'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': '没有权限访问', 'code': 'FORBIDDEN'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '页面不存在', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': '不允许的请求方法', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': '请求过于频繁，请稍后再试', 'code': 'RATE_LIMIT_EXCEEDED'}), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger_service.error(f"Internal server error: {str(error)}", module='error_handler')
        return jsonify({'error': '服务器内部错误', 'code': 'INTERNAL_ERROR'}), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': '文件过大，请上传小于16MB的文件', 'code': 'FILE_TOO_LARGE'}), 413

    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({'error': '不支持的文件类型', 'code': 'UNSUPPORTED_MEDIA_TYPE'}), 415

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({'error': '数据验证失败', 'code': 'VALIDATION_ERROR'}), 422

class PerformanceMonitor:
    def __init__(self):
        self.request_times = []
        self.slow_queries = []

    def record_request_time(self, endpoint, duration):
        self.request_times.append({
            'endpoint': endpoint,
            'duration': duration,
            'timestamp': time.time()
        })
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
        if duration > 1.0:
            self.slow_queries.append({
                'endpoint': endpoint,
                'duration': duration,
                'timestamp': time.time()
            })
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

    def get_stats(self):
        if not self.request_times:
            return {}
        durations = [r['duration'] for r in self.request_times]
        return {
            'total_requests': len(self.request_times),
            'avg_response_time': sum(durations) / len(durations),
            'max_response_time': max(durations),
            'min_response_time': min(durations),
            'slow_requests': len(self.slow_queries)
        }

    def get_slow_requests(self, threshold=1.0):
        return [r for r in self.slow_queries if r['duration'] >= threshold]

performance_monitor = PerformanceMonitor()

def monitor_performance(app):
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.user_id = getattr(g, 'user_id', None)

    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            endpoint = request.endpoint or request.path
            performance_monitor.record_request_time(endpoint, duration)
            response.headers['X-Response-Time'] = f'{duration:.3f}s'
        return response

def require_api_version(*versions):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            accept_header = request.headers.get('Accept', '')
            if 'application/json' not in accept_header:
                accept_header = 'application/json'
            return f(*args, **kwargs)
        return decorated
    return decorator

class APIResponse:
    @staticmethod
    def success(data=None, message='操作成功', meta=None):
        response = {'success': True, 'message': message}
        if data is not None:
            response['data'] = data
        if meta:
            response['meta'] = meta
        return jsonify(response)

    @staticmethod
    def error(message, code=None, details=None, status_code=400):
        return jsonify({
            'success': False,
            'error': {
                'message': message,
                'code': code,
                'details': details
            }
        }), status_code

    @staticmethod
    def paginated(data, page, per_page, total):
        return jsonify({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

api_response = APIResponse()
