#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from app import app
from app.routes.tenders import crawl_progress_store
from datetime import datetime

print('=' * 70)
print('爬虫进度数据查询')
print('=' * 70)
print(f'查询时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'当前任务数: {len(crawl_progress_store)}')
print()

if len(crawl_progress_store) == 0:
    print('没有正在进行的爬虫任务')
else:
    for task_id, progress in crawl_progress_store.items():
        print(f'任务ID: {task_id}')
        print(f'  状态: {progress.get("status")}')
        print(f'  进度百分比: {progress.get("progress_percentage")}%')
        print(f'  已完成: {progress.get("completed")}/{progress.get("total")} 个网站')
        print(f'  已用时间: {progress.get("elapsed_time")}')
        print(f'  预计剩余: {progress.get("estimated_remaining")}')
        print(f'  预计完成: {progress.get("estimated_completion")}')
        print(f'  消息: {progress.get("message")}')
        print()
        print(f'  各网站详细状态:')
        print(f'  {"网站名称":<25} {"状态":<10} {"找到条目":<10} {"耗时(秒)":<10}')
        print(f'  {"-"*55}')
        if progress.get('websites'):
            for ws in progress['websites']:
                name = ws.get('name', '')[:24]
                status = ws.get('status', 'unknown')
                found = ws.get('found', 0)
                duration = ws.get('duration', 0)
                status_icon = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(status, '❓')
                print(f'  {name:<25} {status_icon} {status:<8} {found:<10} {duration:<10}')
        else:
            print('  暂无网站数据')
        print()
        print(f'  当前网站: {progress.get("current_website")}')
        print(f'  结果数量: {len(progress.get("results", []))}')

print()
print('=' * 70)
