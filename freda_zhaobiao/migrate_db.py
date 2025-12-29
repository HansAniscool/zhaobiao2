#!/usr/bin/env python3
"""
数据库迁移脚本
用于将应用从SQLite迁移到PostgreSQL
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from app import app
from app.extensions import db
from app.models import (
    User, Tender, TenderFingerprint, CrawlerTask,
    Favorite, SearchHistory, SystemLog, CrawlHistory, GovernmentWebsite
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库表结构"""
    with app.app_context():
        try:
            logger.info("创建数据库表结构...")
            db.create_all()
            logger.info("数据库表结构创建成功!")
            
            # 创建初始管理员用户
            from werkzeug.security import generate_password_hash
            
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                logger.info("创建初始管理员用户...")
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("初始管理员用户创建成功!")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise

def migrate_data():
    """从SQLite迁移数据到PostgreSQL"""
    with app.app_context():
        try:
            # 这里可以添加数据迁移逻辑
            # 例如从SQLite数据库读取数据并插入到PostgreSQL
            logger.info("数据迁移功能待实现")
            return True
        except Exception as e:
            logger.error(f"数据迁移失败: {str(e)}")
            return False

if __name__ == '__main__':
    logger.info("开始数据库迁移流程...")
    logger.info(f"当前数据库URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        logger.error("请先配置PostgreSQL数据库连接字符串!")
        logger.error("在.env文件中设置DATABASE_URL=postgresql://...")
        sys.exit(1)
    
    init_database()
    migrate_data()
    
    logger.info("数据库迁移流程完成!")