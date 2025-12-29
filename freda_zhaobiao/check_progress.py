#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from app import app
from app.routes.tenders import crawl_progress_store
from datetime import datetime

print('=' * 70)
print('爬虫进度实时监控')
print('=' * 70)

if len(crawl_progress_store) == 0:
    print('当前没有正在进行的搜索任务')
    print()
    print('请在浏览器中访问 http://localhost:5001/search 进行搜索')
else:
    for task_id, progress in crawl_progress_store.items():
        print(f'任务ID: {task_id[:16]}...')
        print(f'  状态: {progress.get("status")}')
        print(f'  进度: {progress.get("progress_percentage")}%')
        print(f'  已完成: {progress.get("completed")}/{progress.get("total")} 个网站')
        print(f'  已用时间: {progress.get("elapsed_time")}')
        print(f'  预计剩余: {progress.get("estimated_remaining")}')
        print(f'  预计完成时间: {progress.get("estimated_completion")}')
        print(f'  消息: {progress.get("message")}')
        
        if progress.get('current_website'):
            cw = progress['current_website']
            print(f'  当前网站: {cw.get("name")}')
            print(f'  网站进度: {cw.get("progress")}/{cw.get("total")}')
            if cw.get('start_time'):
                start = datetime.fromisoformat(cw['start_time'])
                elapsed = (datetime.now() - start).total_seconds()
                print(f'  本网站已爬取: {int(elapsed)}秒')
        
        if progress.get('websites'):
            print()
            print('  各网站状态:')
            for ws in progress['websites'][:5]:
                status_icon = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(ws.get('status'), '❓')
                found = ws.get('found', 0)
                duration = ws.get('duration', 0)
                print(f'  {status_icon} {ws.get("name")[:20]}: {ws.get("status")} (找到{found}条, 耗时{duration}秒)')
            if len(progress['websites']) > 5:
                print(f'  ... 还有 {len(progress["websites"]) - 5} 个网站')

print()
print('=' * 70)
