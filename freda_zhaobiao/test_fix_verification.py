#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复效果：验证URL生成逻辑是否正确处理北京市政府采购网
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.routes.tenders import generate_search_urls


def test_url_generation():
    """测试各种政府网站的URL生成"""
    print("=" * 60)
    print("测试URL生成逻辑修复效果")
    print("=" * 60)
    
    test_cases = [
        {
            'name': '北京市政府采购网',
            'url': 'https://www.ccgp-beijing.gov.cn',
            'query': '测试'
        },
        {
            'name': '中国政府采购网',
            'url': 'https://www.ccgp.gov.cn',
            'query': '测试'
        },
        {
            'name': '天津市政府采购网',
            'url': 'https://www.ccgp-tianjin.gov.cn',
            'query': '测试'
        },
        {
            'name': '上海市政府采购网',
            'url': 'http://www.ccgp-shanghai.gov.cn',
            'query': '测试'
        },
        {
            'name': '中国采购与招标网',
            'url': 'https://www.chinabidding.cn',
            'query': '测试'
        },
        {
            'name': '中国招标投标公共服务平台',
            'url': 'https://www.cpir.cn',
            'query': '测试'
        }
    ]
    
    for test_case in test_cases:
        name = test_case['name']
        url = test_case['url']
        query = test_case['query']
        
        print(f"\n测试: {name}")
        print(f"  基础URL: {url}")
        
        generated_urls = generate_search_urls(url, query)
        
        print(f"  生成的URL列表:")
        for i, gen_url in enumerate(generated_urls, 1):
            print(f"    {i}. {gen_url}")
        
        # 验证是否生成了搜索URL
        has_search_url = any('keyword=' in u or 'keywords=' in u for u in generated_urls)
        has_base_url = url in generated_urls
        
        if has_search_url:
            print(f"  ✓ 成功生成搜索URL")
        else:
            print(f"  ✗ 未生成搜索URL!")
        
        print("-" * 40)


def test_progress_store_update():
    """测试进度存储更新逻辑"""
    print("\n" + "=" * 60)
    print("测试进度存储更新逻辑")
    print("=" * 60)
    
    # 模拟进度存储
    crawl_progress_store = {}
    
    # 模拟开始爬取任务
    task_id = "test-task-123"
    total_websites = 3
    
    crawl_progress_store[task_id] = {
        'status': 'running',
        'total': total_websites,
        'completed': 0,
        'websites': [
            {'name': '北京市政府采购网', 'url': 'https://www.ccgp-beijing.gov.cn', 'status': 'pending'},
            {'name': '中国政府采购网', 'url': 'https://www.ccgp.gov.cn', 'status': 'pending'},
            {'name': '中国采购与招标网', 'url': 'https://www.chinabidding.cn', 'status': 'pending'}
        ],
        'current_website': None,
        'progress_percentage': 0
    }
    
    print(f"\n1. 初始化进度存储:")
    print(f"   任务ID: {task_id}")
    print(f"   网站数量: {total_websites}")
    print(f"   进度: {crawl_progress_store[task_id]['progress_percentage']}%")
    
    # 模拟完成第一个网站
    from datetime import datetime
    
    crawl_progress_store[task_id]['completed'] = 1
    crawl_progress_store[task_id]['websites'][0]['status'] = 'completed'
    crawl_progress_store[task_id]['websites'][0]['found'] = 5
    crawl_progress_store[task_id]['websites'][0]['completed_at'] = datetime.now().isoformat()
    crawl_progress_store[task_id]['current_website'] = {
        'name': crawl_progress_store[task_id]['websites'][1]['name'],
        'progress': 2,
        'total': total_websites
    }
    
    progress_percentage = (1 / 3) * 100
    crawl_progress_store[task_id]['progress_percentage'] = round(progress_percentage, 1)
    
    print(f"\n2. 更新第一个网站完成后:")
    print(f"   完成网站: 1/{total_websites}")
    print(f"   当前网站: {crawl_progress_store[task_id]['current_website']['name']}")
    print(f"   进度: {crawl_progress_store[task_id]['progress_percentage']}%")
    print(f"   第一个网站状态: {crawl_progress_store[task_id]['websites'][0]['status']}")
    print(f"   第一个网站找到条目: {crawl_progress_store[task_id]['websites'][0]['found']}")
    
    # 模拟完成第二个网站
    crawl_progress_store[task_id]['completed'] = 2
    crawl_progress_store[task_id]['websites'][1]['status'] = 'completed'
    crawl_progress_store[task_id]['websites'][1]['found'] = 3
    crawl_progress_store[task_id]['websites'][1]['completed_at'] = datetime.now().isoformat()
    crawl_progress_store[task_id]['current_website'] = {
        'name': crawl_progress_store[task_id]['websites'][2]['name'],
        'progress': 3,
        'total': total_websites
    }
    
    progress_percentage = (2 / 3) * 100
    crawl_progress_store[task_id]['progress_percentage'] = round(progress_percentage, 1)
    
    print(f"\n3. 更新第二个网站完成后:")
    print(f"   完成网站: 2/{total_websites}")
    print(f"   当前网站: {crawl_progress_store[task_id]['current_website']['name']}")
    print(f"   进度: {crawl_progress_store[task_id]['progress_percentage']}%")
    
    # 模拟完成第三个网站
    crawl_progress_store[task_id]['completed'] = 3
    crawl_progress_store[task_id]['websites'][2]['status'] = 'completed'
    crawl_progress_store[task_id]['websites'][2]['found'] = 2
    crawl_progress_store[task_id]['websites'][2]['completed_at'] = datetime.now().isoformat()
    crawl_progress_store[task_id]['current_website'] = None
    crawl_progress_store[task_id]['status'] = 'completed'
    crawl_progress_store[task_id]['progress_percentage'] = 100
    
    print(f"\n4. 更新第三个网站完成后:")
    print(f"   完成网站: 3/{total_websites}")
    print(f"   当前网站: 无 (已完成)")
    print(f"   进度: {crawl_progress_store[task_id]['progress_percentage']}%")
    print(f"   任务状态: {crawl_progress_store[task_id]['status']}")
    
    # 统计总结果
    total_found = sum(site.get('found', 0) for site in crawl_progress_store[task_id]['websites'])
    print(f"\n5. 总计:")
    print(f"   找到招标信息: {total_found} 条")
    print(f"   成功爬取: {sum(1 for s in crawl_progress_store[task_id]['websites'] if s['status'] == 'completed')}/{total_websites} 个网站")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    test_url_generation()
    test_progress_store_update()
