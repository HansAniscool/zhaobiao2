#!/usr/bin/env python3
import sys
import time
sys.path.insert(0, '.')
from app import app
from app.routes.tenders import crawl_progress_store
from datetime import datetime

print('检查爬虫任务状态...')
print()

time.sleep(2)

if len(crawl_progress_store) == 0:
    print('没有找到爬虫任务')
    print()
    print('可能的原因：')
    print('1. 搜索请求没有到达服务器')
    print('2. 数据库中没有可用的政府网站 (GovernmentWebsite.status="active")')
    print('3. 已有搜索结果，不需要爬虫')
    print()
    
    try:
        from app.extensions import db
        from app.models import GovernmentWebsite
        
        with app.app_context():
            websites = GovernmentWebsite.query.all()
            active_websites = GovernmentWebsite.query.filter_by(status='active').all()
            print(f'数据库中的政府网站总数: {len(websites)}')
            print(f'状态为active的网站数: {len(active_websites)}')
            if active_websites:
                print('Active网站列表:')
                for w in active_websites:
                    print(f'  - {w.name}: {w.website} ({w.status})')
            else:
                print('没有状态为active的网站，爬虫不会启动')
    except Exception as e:
        print(f'检查数据库时出错: {e}')
else:
    print(f'找到 {len(crawl_progress_store)} 个爬虫任务')
    for task_id, progress in crawl_progress_store.items():
        print(f'任务: {task_id[:20]}...')
        print(f'状态: {progress.get("status")}')
        print(f'进度: {progress.get("completed")}/{progress.get("total")}')
