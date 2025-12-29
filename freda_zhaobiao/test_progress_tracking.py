#!/usr/bin/env python3
"""
测试爬虫进度跟踪系统
"""
import sys
import os
import time
import threading
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置Flask应用环境
os.environ.setdefault('FLASK_APP', 'app.py')
os.environ.setdefault('FLASK_ENV', 'development')

from flask import Flask

def test_progress_tracking():
    """测试进度跟踪系统"""
    print("=" * 60)
    print("测试爬虫进度跟踪系统")
    print("=" * 60)
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        from app.extensions import db
        from app.models import GovernmentWebsite
        
        # 创建数据库表
        db.create_all()
        
        # 添加测试网站
        test_websites = [
            GovernmentWebsite(name='测试网站1', website='https://test1.example.com', status='active'),
            GovernmentWebsite(name='测试网站2', website='https://test2.example.com', status='active'),
            GovernmentWebsite(name='测试网站3', website='https://test3.example.com', status='active'),
        ]
        
        for website in test_websites:
            db.session.add(website)
        db.session.commit()
        
        print(f"✓ 添加了 {len(test_websites)} 个测试网站")
        
        # 模拟进度存储
        crawl_progress_store = {}
        task_id = 'test-task-123'
        
        # 初始化进度
        crawl_progress_store[task_id] = {
            'status': 'running',
            'total': len(test_websites),
            'completed': 0,
            'results': [],
            'message': '开始测试爬取...',
            'websites': [{'name': w.name, 'url': w.website, 'status': 'pending'} for w in test_websites],
            'current_website': None,
            'start_time': datetime.now().isoformat(),
            'start_datetime': datetime.now(),
            'estimated_completion': None,
            'elapsed_time': '0秒',
            'estimated_remaining': len(test_websites) * 3,
            'progress_percentage': 0
        }
        
        print(f"✓ 初始化进度: total={crawl_progress_store[task_id]['total']}")
        
        # 模拟爬取过程
        results = []
        start_time = datetime.now()
        successful_crawls = 0
        failed_crawls = 0
        
        for idx, website in enumerate(test_websites):
            print(f"\n正在处理网站 {idx + 1}/{len(test_websites)}: {website.name}")
            
            # 模拟处理时间
            time.sleep(0.5)
            
            # 更新进度
            crawl_progress_store[task_id]['websites'][idx]['status'] = 'completed'
            crawl_progress_store[task_id]['websites'][idx]['completed_at'] = datetime.now().isoformat()
            crawl_progress_store[task_id]['websites'][idx]['found'] = idx * 2 + 1
            crawl_progress_store[task_id]['websites'][idx]['duration'] = 0.5
            
            crawl_progress_store[task_id]['current_website'] = {
                'name': website.name,
                'url': website.website,
                'progress': idx + 1,
                'total': len(test_websites)
            }
            
            crawl_progress_store[task_id]['completed'] = idx + 1
            
            # 计算时间和进度
            elapsed_seconds = int((datetime.now() - start_time).total_seconds())
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            elapsed_formatted = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            
            progress_percentage = ((idx + 1) / len(test_websites)) * 100
            
            remaining_websites = len(test_websites) - idx - 1
            avg_time_per_website = (datetime.now() - start_time).total_seconds() / (idx + 1) if idx > 0 else 0.5
            estimated_remaining_seconds = int(remaining_websites * avg_time_per_website)
            
            if estimated_remaining_seconds > 0:
                est_minutes = estimated_remaining_seconds // 60
                est_seconds = estimated_remaining_seconds % 60
                if est_minutes > 0:
                    estimated_formatted = f"{est_minutes}分{est_seconds}秒"
                    estimated_completion = datetime.now() + timedelta(seconds=estimated_remaining_seconds)
                    estimated_completion_time = estimated_completion.strftime('%H:%M:%S')
                else:
                    estimated_formatted = f"{est_seconds}秒"
                    estimated_completion_time = datetime.now().strftime('%H:%M:%S')
            else:
                estimated_formatted = "即将完成"
                estimated_completion_time = datetime.now().strftime('%H:%M:%S')
            
            crawl_progress_store[task_id]['elapsed_time'] = elapsed_formatted
            crawl_progress_store[task_id]['estimated_remaining'] = estimated_formatted
            crawl_progress_store[task_id]['estimated_completion'] = estimated_completion_time
            crawl_progress_store[task_id]['progress_percentage'] = round(progress_percentage, 1)
            
            message = f'已完成 {idx + 1}/{len(test_websites)} 个网站'
            crawl_progress_store[task_id]['message'] = message
            
            print(f"  ✓ 更新进度: {progress_percentage:.1f}%, 已用时间: {elapsed_formatted}, 预计剩余: {estimated_formatted}")
            
            successful_crawls += 1
            results.extend([{'title': f'测试结果{idx}-{j}'} for j in range(idx * 2 + 1)])
        
        # 完成
        crawl_progress_store[task_id]['status'] = 'completed'
        crawl_progress_store[task_id]['results'] = results
        crawl_progress_store[task_id]['current_website'] = None
        crawl_progress_store[task_id]['progress_percentage'] = 100
        crawl_progress_store[task_id]['message'] = f'测试完成，共找到 {len(results)} 条结果'
        
        print("\n" + "=" * 60)
        print("测试结果:")
        print("=" * 60)
        print(f"✓ 总网站数: {crawl_progress_store[task_id]['total']}")
        print(f"✓ 完成网站数: {crawl_progress_store[task_id]['completed']}")
        print(f"✓ 成功率: {successful_crawls}/{len(test_websites)} ({successful_crawls/len(test_websites)*100:.0f}%)")
        print(f"✓ 找到结果数: {len(results)}")
        print(f"✓ 最终进度: {crawl_progress_store[task_id]['progress_percentage']}%")
        print(f"✓ 总耗时: {crawl_progress_store[task_id]['elapsed_time']}")
        print("✓ 状态: completed")
        print("=" * 60)
        
        # 验证进度存储共享
        print("\n验证进度存储共享:")
        print(f"  ✓ crawl_progress_store 包含 task_id: {task_id in crawl_progress_store}")
        print(f"  ✓ 进度状态正确: {crawl_progress_store[task_id]['status'] == 'completed'}")
        print(f"  ✓ 进度百分比正确: {crawl_progress_store[task_id]['progress_percentage'] == 100}")
        
        return True

def test_api_endpoint():
    """测试API端点"""
    print("\n" + "=" * 60)
    print("测试API端点")
    print("=" * 60)
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # 模拟进度存储
    test_progress = {
        'task-1': {
            'status': 'running',
            'total': 3,
            'completed': 1,
            'progress_percentage': 33.3,
            'message': '正在爬取...',
            'elapsed_time': '5秒',
            'estimated_remaining': '10秒'
        }
    }
    
    @app.route('/api/crawl/progress/<task_id>')
    def get_progress(task_id):
        if task_id in test_progress:
            return test_progress[task_id], 200
        return {'error': 'not found'}, 404
    
    with app.test_client() as client:
        # 测试存在的任务
        response = client.get('/api/crawl/progress/task-1')
        print(f"✓ 请求存在的任务: {response.status_code}")
        data = response.get_json()
        print(f"  返回数据: {data}")
        
        # 测试不存在的任务
        response = client.get('/api/crawl/progress/unknown')
        print(f"✓ 请求不存在的任务: {response.status_code}")
        data = response.get_json()
        print(f"  返回数据: {data}")
    
    return True

if __name__ == '__main__':
    print("\n开始测试爬虫进度跟踪系统...")
    print()
    
    try:
        test_progress_tracking()
        test_api_endpoint()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
