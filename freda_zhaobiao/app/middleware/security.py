from flask import request, g, jsonify
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
import time
import hashlib
import re
from ..services.logger_service import logger_service

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.api_calls = defaultdict(list)

    def _get_client_key(self):
        if request.is_json:
            api_key = request.headers.get('X-API-Key', '')
            if api_key:
                return f"apikey:{api_key}"
        return f"ip:{request.remote_addr}"

    def _cleanup_old_requests(self, requests_list, max_age):
        cutoff = datetime.utcnow() - max_age
        return [r for r in requests_list if r > cutoff]

    def is_rate_limited(self, limit, period, window_type='sliding'):
        key = self._get_client_key()
        now = datetime.utcnow()
        max_age = timedelta(seconds=period)
        
        if window_type == 'sliding':
            self.requests[key] = self._cleanup_old_requests(self.requests[key], max_age)
            if len(self.requests[key]) >= limit:
                return True
            self.requests[key].append(now)
            return False
        else:
            minute_ago = now - timedelta(minutes=1)
            recent = [r for r in self.requests[key] if r > minute_ago]
            if len(recent) >= limit:
                return True
            self.requests[key].append(now)
            return False

    def is_api_rate_limited(self, limit, period):
        key = self._get_client_key()
        now = datetime.utcnow()
        self.api_calls[key] = self._cleanup_old_requests(self.api_calls[key], timedelta(seconds=period))
        
        if len(self.api_calls[key]) >= limit:
            return True
        self.api_calls[key].append(now)
        return False

    def get_remaining(self, limit, period):
        key = self._get_client_key()
        self.requests[key] = self._cleanup_old_requests(self.requests[key], timedelta(seconds=period))
        return max(0, limit - len(self.requests[key]))

    def reset(self, key=None):
        if key:
            if key in self.requests:
                del self.requests[key]
            if key in self.api_calls:
                del self.api_calls[key]
        else:
            self.requests.clear()
            self.api_calls.clear()

rate_limiter = RateLimiter()

def rate_limit(limit, period, message=None, window_type='sliding'):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if rate_limiter.is_rate_limited(limit, period, window_type):
                logger_service.warning(
                    f"Rate limit exceeded for {request.remote_addr}: {request.path}",
                    module='rate_limit'
                )
                remaining = 0
            else:
                remaining = rate_limiter.get_remaining(limit, period)
            
            response = f(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Period'] = str(period)
            
            if rate_limiter.is_rate_limited(limit, period, window_type):
                if hasattr(response, 'status_code'):
                    response.status_code = 429
                return jsonify({
                    'error': message or '请求过于频繁，请稍后再试',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'retry_after': period
                }), 429
            
            return response
        return decorated
    return decorator

def api_rate_limit(limit, period=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if rate_limiter.is_api_rate_limited(limit, period):
                logger_service.warning(
                    f"API rate limit exceeded for {request.remote_addr}: {request.path}",
                    module='rate_limit'
                )
                return jsonify({
                    'error': 'API请求过于频繁',
                    'code': 'API_RATE_LIMIT_EXCEEDED',
                    'retry_after': period
                }), 429
            return f(*args, **kwargs)
        return decorated
    return decorator

class SecurityMiddleware:
    SENSITIVE_PATTERNS = [
        re.compile(r'password[\s]*=[\s]*[^\s,\'"]+', re.I),
        re.compile(r'secret[\s]*=[\s]*[^\s,\'"]+', re.I),
        re.compile(r'key[\s]*=[\s]*[^\s,\'"]+', re.I),
        re.compile(r'token[\s]*=[\s]*[^\s,\'"]+', re.I),
        re.compile(r'Authorization[\s]*:[\s]*[^\s]+'),
    ]

    @staticmethod
    def sanitize_input(value):
        if isinstance(value, str):
            value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.I | re.DOTALL)
            value = re.sub(r'javascript:', '', value, flags=re.I)
            value = re.sub(r'on\w+\s*=', '', value)
            value = value.strip()
            return value
        elif isinstance(value, dict):
            return {k: SecurityMiddleware.sanitize_input(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [SecurityMiddleware.sanitize_input(item) for item in value]
        return value

    @staticmethod
    def check_sensitive_data(data):
        if isinstance(data, str):
            for pattern in SecurityMiddleware.SENSITIVE_PATTERNS:
                if pattern.search(data):
                    return True
        elif isinstance(data, dict):
            sensitive_keys = ['password', 'secret', 'key', 'token', 'authorization']
            for key in sensitive_keys:
                if key in data:
                    return True
        return False

    @staticmethod
    def validate_content_length(max_size=1024*1024):
        content_length = request.content_length
        if content_length and content_length > max_size:
            logger_service.warning(
                f"Content length exceeded: {content_length} bytes from {request.remote_addr}",
                module='security'
            )
            return False
        return True

    @staticmethod
    def check_sql_injection(value):
        if isinstance(value, str):
            suspicious = [
                r"'\s*OR\s+'1'\s*=\s*'1'",
                r"'\s*UNION\s+",
                r"\s+DROP\s+TABLE",
                r"\s+DELETE\s+FROM",
                r"\s+INSERT\s+INTO",
                r"--\s*$",
                r"/\*.*\*/",
                r"EXEC\s*\(",
                r"xp_cmdshell",
            ]
            for pattern in suspicious:
                if re.search(pattern, value, re.I):
                    return True
        return False

security = SecurityMiddleware()

def require_content_type(*content_types):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            content_type = request.content_type
            if not content_type:
                return jsonify({'error': 'Content-Type required'}), 400
            
            valid = any(ct in content_type for ct in content_types)
            if not valid:
                return jsonify({
                    'error': f'Content-Type must be one of: {", ".join(content_types)}'
                }), 415
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def sanitize_params(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        for key, value in request.args.items():
            request.args[key] = SecurityMiddleware.sanitize_input(value)
        
        if request.is_json:
            try:
                data = request.get_json(silent=True)
                if data:
                    request.sanitized_json = SecurityMiddleware.sanitize_input(data)
            except:
                pass
        
        return f(*args, **kwargs)
    return decorated

def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

class RequestValidator:
    @staticmethod
    def validate_pagination_params(page, per_page, max_per_page=100):
        try:
            page = int(page)
            per_page = int(per_page)
            if page < 1:
                page = 1
            if per_page < 1:
                per_page = 20
            if per_page > max_per_page:
                per_page = max_per_page
            return page, per_page
        except (TypeError, ValueError):
            return 1, 20

    @staticmethod
    def validate_date_range(date_from, date_to):
        try:
            from datetime import datetime
            date_from_obj = None
            date_to_obj = None
            
            if date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            if date_from_obj and date_to_obj and date_from_obj > date_to_obj:
                return None, None
            
            return date_from_obj, date_to_obj
        except ValueError:
            return None, None

    @staticmethod
    def validate_search_query(query, max_length=500):
        if not query:
            return ''
        query = str(query)[:max_length]
        query = re.sub(r'[<>]', '', query)
        return query.strip()

request_validator = RequestValidator()
