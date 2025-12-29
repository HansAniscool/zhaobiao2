#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app import app
from app.routes.tenders import crawl_progress_store, start_crawl_task
import uuid

print("测试后台爬取任务...")
print("初始状态 - store 中的任务数:", len(crawl_progress_store))

# 创建一个测试任务ID
task_id = str(uuid.uuid4())
print("测试任务ID:", task_id[:8], "...")

# 在应用上下文中直接运行爬取任务（不通过线程）
with app.app_context():
    print("开始执行爬取任务...")
    start_crawl_task(task_id, "测试关键词", None)
    
    # 检查进度
    if task_id in crawl_progress_store:
        progress = crawl_progress_store[task_id]
        print("任务状态:", progress.get('status'))
        print("总网站数:", progress.get('total'))
        print("已完成:", progress.get('completed'))
        print("进度百分比:", progress.get('progress_percentage'), "%")
        print("消息:", progress.get('message'))
    else:
        print("错误: 任务未在进度存储中找到!")
        
    # 清理
    if task_id in crawl_progress_store:
        del crawl_progress_store[task_id]
    print("清理后 - store 中的任务数:", len(crawl_progress_store))

print("\n测试完成!")
