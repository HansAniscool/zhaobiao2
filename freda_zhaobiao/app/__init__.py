from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_wtf import CSRFProtect
from .extensions import db
from .models import login_manager
import config as config_module

app = Flask(__name__)
app.config.from_object(config_module)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
cache = Cache(app)
csrf = CSRFProtect(app)

from .models import User, Tender, CrawlerTask, Favorite, SearchHistory, SystemLog
from .routes import auth, tenders, crawler, admin, api

app.register_blueprint(auth.bp)
app.register_blueprint(tenders.bp)
app.register_blueprint(crawler.bp)
app.register_blueprint(admin.bp, url_prefix='/admin')
app.register_blueprint(api.bp)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
