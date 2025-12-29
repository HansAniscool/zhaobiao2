import os
from logging import INFO

# 招标信息收集系统 - 配置文件
# ======================================

# 应用配置
APP_NAME = "招标信息收集系统"
APP_VERSION = "1.0.0"
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
PERMANENT_SESSION_LIFETIME = 86400
FLASK_RUN_PORT = os.environ.get('FLASK_RUN_PORT', '5001')

# 数据库配置
DATABASE_PATH = 'data/tender.db'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath(DATABASE_PATH)}')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 文件上传配置
UPLOAD_FOLDER = 'uploads/'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# 爬虫配置
CRAWLER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CRAWLER_REQUEST_DELAY = 2
CRAWLER_MAX_RETRY = 3
CRAWLER_TIMEOUT = 30

# 日志配置
LOG_LEVEL = INFO
LOG_FILE = 'logs/app.log'
LOG_MAX_BYTES = 10485760
LOG_BACKUP_COUNT = 5

# 搜索配置
SEARCH_PER_PAGE = 20
SEARCH_MAX_KEYWORDS = 10

# 缓存配置
CACHE_TYPE = "simple"
CACHE_DEFAULT_TIMEOUT = 300

# 阿里云域名配置（可选）
# ALIYUN_ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
# ALIYUN_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
# DOMAIN_ZONE = os.environ.get('DOMAIN_ZONE')
