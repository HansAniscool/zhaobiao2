import sys
sys.path.insert(0, '.')

from app import app
from app.routes.tenders import crawl_progress_store
from datetime import datetime

print('=== 测试进度跟踪系统 ===')

# 检查 crawl_progress_store 是否存在
print(f'1. crawl_progress_store 存在: {type(crawl_progress_store).__name__}')
print(f'   初始任务数: {len(crawl_progress_store)}')

# 模拟创建一个任务
test_task_id = 'test-task-001'
crawl_progress_store[test_task_id] = {
    'status': 'running',
    'total': 5,
    'completed': 2,
    'message': '测试任务运行中',
    'websites': [
        {'name': '网站1', 'url': 'http://site1.com', 'status': 'completed'},
        {'name': '网站2', 'url': 'http://site2.com', 'status': 'completed'},
        {'name': '网站3', 'url': 'http://site3.com', 'status': 'running'},
        {'name': '网站4', 'url': 'http://site4.com', 'status': 'pending'},
        {'name': '网站5', 'url': 'http://site5.com', 'status': 'pending'}
    ],
    'current_website': {
        'name': '网站3',
        'url': 'http://site3.com',
        'progress': 3,
        'total': 5,
        'start_time': datetime.now().isoformat()
    },
    'start_time': datetime.now().isoformat(),
    'start_datetime': datetime.now(),
    'elapsed_time': '1分30秒',
    'estimated_remaining': 180,
    'progress_percentage': 40.0
}

print(f'2. 创建测试任务后任务数: {len(crawl_progress_store)}')
print(f'   任务存在: {test_task_id in crawl_progress_store}')

# 验证 API 端点
from app.routes.api import get_crawl_progress

with app.test_request_context(f'/api/crawl/progress/{test_task_id}'):
    response = get_crawl_progress(test_task_id)
    data = response.get_json()
    
    print(f'3. API 返回状态码: {response.status_code}')
    print(f'   任务状态: {data.get("status")}')
    print(f'   完成进度: {data.get("completed")}/{data.get("total")}')
    print(f'   进度百分比: {data.get("progress_percentage")}%')
    print(f'   当前网站: {data.get("current_website", {}).get("name")}')

# 清理测试数据
del crawl_progress_store[test_task_id]
print(f'4. 清理后任务数: {len(crawl_progress_store)}')

print('=== 测试完成 ===')
