from flask import request
from ..extensions import db, cache
from ..models import Tender
from functools import wraps
from sqlalchemy import event
from sqlalchemy.engine import Engine
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop()
    if total > 0.1:
        logging.warning(f"Slow query ({total:.3f}s): {statement[:100]}")

def cached_with_timeout(timeout=300, cache_key_prefix=''):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f"{cache_key_prefix}:{request.url}"
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        return decorated_function
    return decorator

def cache_key_builder(*args, **kwargs):
    key_parts = []
    for arg in args:
        key_parts.append(str(arg))
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={value}")
    return ':'.join(key_parts)

def cached_query(timeout=300, prefix='query'):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            cache_key = f"{prefix}:{cache_key_builder(*args, **kwargs)}"
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            result = f(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated
    return decorator

def invalidate_cache(pattern):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            result = f(*args, **kwargs)
            if pattern == 'all':
                cache.clear()
            else:
                keys_to_delete = []
                for key in cache.cache.keys():
                    if pattern in key:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    cache.delete(key)
            return result
        return decorated
    return decorator

class QueryOptimizer:
    @staticmethod
    def optimize_tender_query(base_query, page=1, per_page=20):
        optimized = base_query
        optimized = optimized.options(
            db.selectinload(Tender.favorites),
            db.selectinload(Tender.fingerprints)
        )
        optimized = optimized.limit(per_page).offset((page - 1) * per_page)
        return optimized

    @staticmethod
    def add_eager_loads(query):
        return query.options(
            db.joinedload(Tender.user),
            db.selectinload(Tender.favorites)
        )

    @staticmethod
    def paginate_query(query, page, per_page, error_out=False):
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100
        
        total = query.count()
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        if error_out and page > pages and pages > 0:
            return None
        
        items = query.limit(per_page).offset((page - 1) * per_page).all()
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
            'has_prev': page > 1,
            'has_next': page < pages
        }

    @staticmethod
    def batch_query(model, ids, batch_size=100):
        results = []
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            items = model.query.filter(model.id.in_(batch)).all()
            results.extend(items)
        return results

    @staticmethod
    def count_with_filter(model, filters):
        query = model.query
        for attr, value in filters.items():
            if value is not None:
                query = query.filter(getattr(model, attr) == value)
        return query.count()

    @staticmethod
    def search_tenders(query_string, filters=None, page=1, per_page=20):
        base = Tender.query.filter(Tender.status == 'active')
        
        if query_string:
            search = f'%{query_string}%'
            base = base.filter(
                db.or_(
                    Tender.title.ilike(search),
                    Tender.summary.ilike(search),
                    Tender.organization.ilike(search)
                )
            )
        
        if filters:
            if filters.get('category'):
                base = base.filter(Tender.category == filters['category'])
            if filters.get('location'):
                base = base.filter(Tender.location.ilike(f'%{filters["location"]}%'))
            if filters.get('date_from'):
                base = base.filter(Tender.publish_date >= filters['date_from'])
            if filters.get('date_to'):
                base = base.filter(Tender.publish_date <= filters['date_to'])
        
        base = base.order_by(Tender.publish_date.desc())
        
        return QueryOptimizer.paginate_query(base, page, per_page)

    @staticmethod
    def get_popular_tenders(limit=10, days=7):
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return Tender.query.filter(
            Tender.status == 'active',
            Tender.created_at >= cutoff
        ).order_by(
            Tender.view_count.desc()
        ).limit(limit).all()

    @staticmethod
    def get_recent_tenders(limit=10):
        return Tender.query.filter(
            Tender.status == 'active'
        ).order_by(
            Tender.publish_date.desc()
        ).limit(limit).all()

query_optimizer = QueryOptimizer()

class CacheManager:
    STATIC_KEYS = {
        'stats': 'app:stats',
        'categories': 'app:categories',
        'home_tenders': 'app:home_tenders',
    }

    @staticmethod
    def get_stats():
        cached = cache.get(CacheManager.STATIC_KEYS['stats'])
        if cached:
            return cached
        
        from models import Tender
        stats = {
            'total': Tender.query.count(),
            'today': Tender.query.filter(
                db.func.date(Tender.publish_date) == db.func.current_date()
            ).count(),
            'this_week': Tender.query.filter(
                Tender.publish_date >= db.func.date(db.func.now(), '-7 days')
            ).count(),
            'this_month': Tender.query.filter(
                Tender.publish_date >= db.func.date(db.func.now(), '-30 days')
            ).count()
        }
        cache.set(CacheManager.STATIC_KEYS['stats'], stats, timeout=600)
        return stats

    @staticmethod
    def invalidate_stats():
        cache.delete(CacheManager.STATIC_KEYS['stats'])

    @staticmethod
    def get_home_tenders():
        cached = cache.get(CacheManager.STATIC_KEYS['home_tenders'])
        if cached:
            return cached
        
        tenders = query_optimizer.get_recent_tenders(10)
        cache.set(CacheManager.STATIC_KEYS['home_tenders'], tenders, timeout=300)
        return tenders

    @staticmethod
    def invalidate_home():
        cache.delete(CacheManager.STATIC_KEYS['home_tenders'])

    @staticmethod
    def cache_tender_detail(tender_id, data):
        key = f'tender:{tender_id}'
        cache.set(key, data, timeout=600)

    @staticmethod
    def get_tender_detail(tender_id):
        key = f'tender:{tender_id}'
        return cache.get(key)

    @staticmethod
    def invalidate_tender(tender_id):
        cache.delete(f'tender:{tender_id}')
        CacheManager.invalidate_stats()
        CacheManager.invalidate_home()

cache_manager = CacheManager()

def with_cache(key, timeout=300):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            cache_key = f"{key}:{cache_key_builder(*args, **kwargs)}"
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            result = f(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated
    return decorator
