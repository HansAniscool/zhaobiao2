from ..models import SearchHistory, Tender
from ..extensions import db
from datetime import datetime

def save_search_history(keywords, date_from=None, date_to=None, category=None, user_id=None, result_count=0):
    try:
        filters = {}
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if category:
            filters['category'] = category
        
        history = SearchHistory(
            user_id=user_id,
            keywords=keywords,
            filters=str(filters) if filters else None,
            result_count=result_count
        )
        db.session.add(history)
        db.session.commit()
        return history.id
    except Exception as e:
        db.session.rollback()
        return None

def update_search_history(history_id, result_count):
    try:
        history = SearchHistory.query.get(history_id)
        if history:
            history.result_count = result_count
            db.session.commit()
            return True
        return False
    except Exception:
        db.session.rollback()
        return False

def get_search_history(user_id=None, limit=100):
    query = SearchHistory.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.order_by(SearchHistory.created_at.desc()).limit(limit).all()

def delete_search_history(history_id, user_id=None):
    try:
        query = SearchHistory.query.filter_by(id=history_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        history = query.first()
        if history:
            db.session.delete(history)
            db.session.commit()
            return True
        return False
    except Exception:
        db.session.rollback()
        return False

def clear_search_history(user_id=None):
    try:
        query = SearchHistory.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        query.delete()
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

def format_date(date_obj):
    if not date_obj:
        return ''
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime('%Y-%m-%d')

def truncate_text(text, max_length=100):
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'

def get_pagination_range(page, total_pages, delta=2):
    if total_pages <= 1:
        return [1]
    
    range_start = max(1, page - delta)
    range_end = min(total_pages, page + delta)
    
    while range_end - range_start < 2 * delta and range_end - range_start < total_pages - 1:
        if range_start > 1:
            range_start -= 1
        if range_end < total_pages:
            range_end += 1
    
    return list(range(range_start, range_end + 1))
