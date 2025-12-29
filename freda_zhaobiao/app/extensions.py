from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()
csrf = CSRFProtect()

def init_app(app):
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)
