from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    tenders = db.relationship('Tender', backref='user', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    search_histories = db.relationship('SearchHistory', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Tender(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    publish_date = db.Column(db.Date, nullable=False, index=True)
    publish_time = db.Column(db.Time, nullable=True)
    organization = db.Column(db.String(200), nullable=True, index=True)
    location = db.Column(db.String(100), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(1000), nullable=True)
    source_website = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='active')
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    fingerprints = db.relationship('TenderFingerprint', backref='tender', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='tender', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'organization': self.organization,
            'location': self.location,
            'summary': self.summary,
            'source_url': self.source_url,
            'source_website': self.source_website,
            'category': self.category,
            'status': self.status,
            'view_count': self.view_count
        }

class TenderFingerprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tender.id'), nullable=False)
    fingerprint = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CrawlerTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(200), nullable=False)
    keywords = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    crawl_interval = db.Column(db.Integer, default=3600)  # 秒
    last_crawl_time = db.Column(db.DateTime, nullable=True)
    next_crawl_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')
    total_crawled = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tender_id = db.Column(db.Integer, db.ForeignKey('tender.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    keywords = db.Column(db.String(500), nullable=False)
    filters = db.Column(db.Text, nullable=True)
    result_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)
    module = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=False)
    traceback = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class CrawlHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('crawler_task.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    items_found = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    items_updated = db.Column(db.Integer, default=0)
    items_skipped = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)

class GovernmentWebsite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(500), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    level = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    total_crawled = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    last_crawl_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

from flask_login import LoginManager

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
