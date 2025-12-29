import sys
import time
import threading
sys.path.insert(0, '.')

from app import app
from app.routes.tenders import crawl_progress_store, start_crawl_task
from datetime import datetime

print('=== 测试真实搜索场景 ===')

# 模拟启动搜索时的操作
with app.app_context():
    # 获取活跃网站数量
    from app.models import GovernmentWebsite
    websites = GovernmentWebsite.query.filter_by(status='active').all()
    print(f'1. 活跃网站数量: {len(websites)}')
    
    if len(websites) == 0:
        print('警告: 没有活跃的网站，将无法测试爬取功能')
    else:
        # 创建任务ID
        task_id = 'real-test-task-001'
        
        # 在后台线程中启动爬取任务
        def run_crawl():
            with app.app_context():
                start_crawl_task(task_id, '测试关键词', '')
        
        thread = threading.Thread(target=run_crawl)
        thread.start()
        
        print(f'2. 启动爬取线程，任务ID: {task_id}')
        print(f'   初始任务数: {len(crawl_progress_store)}')
        
        # 等待并检查进度
        for i in range(5):
            time.sleep(2)  # 等待2秒
            print(f'\n--- 第 {i+1} 次检查 ---')
            
            if task_id in crawl_progress_store:
                progress = crawl_progress_store[task_id]
                print(f'   任务状态: {progress.get("status")}')
                print(f'   完成进度: {progress.get("completed")}/{progress.get("total")}')
                print(f'   进度百分比: {progress.get("progress_percentage")}%')
                print(f'   当前网站: {progress.get("current_website", {}).get("name") if progress.get("current_website") else "无"}')
                print(f'   消息: {progress.get("message")}')
                
                if progress.get('status') == 'completed':
                    print('\n爬取任务已完成!')
                    break
            else:
                print('   任务尚未创建')
        
        # 清理
        if task_id in crawl_progress_store:
            del crawl_progress_store[task_id]
            print(f'\n清理后任务数: {len(crawl_progress_store)}')

print('\n=== 测试完成 ===')
