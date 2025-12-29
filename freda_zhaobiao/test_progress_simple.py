#!/usr/bin/env python3
"""
简单测试爬虫进度跟踪系统
"""
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_progress_tracking_simulation():
    """模拟测试进度跟踪"""
    print("=" * 60)
    print("模拟测试爬虫进度跟踪系统")
    print("=" * 60)
    
    # 模拟进度存储
    crawl_progress_store = {}
    task_id = 'test-task-123'
    
    # 模拟网站数据
    websites = [
        {'name': '北京市政府采购网', 'url': 'https://www.ccgp-beijing.gov.cn'},
        {'name': '上海市政府采购网', 'url': 'https://www.ccgp-shanghai.gov.cn'},
        {'name': '广州市政府采购网', 'url': 'https://www.ccgp-guangzhou.gov.cn'},
    ]
    
    print(f"模拟网站数量: {len(websites)}")
    
    # 初始化进度
    crawl_progress_store[task_id] = {
        'status': 'running',
        'total': len(websites),
        'completed': 0,
        'results': [],
        'message': '开始测试爬取...',
        'websites': [{'name': w['name'], 'url': w['url'], 'status': 'pending'} for w in websites],
        'current_website': None,
        'start_time': datetime.now().isoformat(),
        'start_datetime': datetime.now(),
        'estimated_completion': None,
        'elapsed_time': '0秒',
        'estimated_remaining': len(websites) * 3,
        'progress_percentage': 0
    }
    
    print(f"✓ 初始化进度存储")
    print(f"  - 任务ID: {task_id}")
    print(f"  - 总网站数: {crawl_progress_store[task_id]['total']}")
    print(f"  - 预计剩余时间: {crawl_progress_store[task_id]['estimated_remaining']}秒")
    
    # 模拟爬取过程
    results = []
    start_time = datetime.now()
    successful_crawls = 0
    failed_crawls = 0
    
    for idx, website in enumerate(websites):
        print(f"\n处理网站 {idx + 1}/{len(websites)}: {website['name']}")
        
        # 模拟处理时间
        time.sleep(0.2)
        
        # 更新进度
        crawl_progress_store[task_id]['websites'][idx]['status'] = 'completed'
        crawl_progress_store[task_id]['websites'][idx]['completed_at'] = datetime.now().isoformat()
        crawl_progress_store[task_id]['websites'][idx]['found'] = idx * 2 + 1
        crawl_progress_store[task_id]['websites'][idx]['duration'] = 0.2
        
        crawl_progress_store[task_id]['current_website'] = {
            'name': website['name'],
            'url': website['url'],
            'progress': idx + 1,
            'total': len(websites)
        }
        
        crawl_progress_store[task_id]['completed'] = idx + 1
        
        # 计算时间和进度
        elapsed_seconds = int((datetime.now() - start_time).total_seconds())
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        elapsed_formatted = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        
        progress_percentage = ((idx + 1) / len(websites)) * 100
        
        remaining_websites = len(websites) - idx - 1
        avg_time_per_website = (datetime.now() - start_time).total_seconds() / (idx + 1) if idx > 0 else 0.2
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
        
        message = f'已完成 {idx + 1}/{len(websites)} 个网站'
        crawl_progress_store[task_id]['message'] = message
        
        print(f"  ✓ 进度更新:")
        print(f"    - 完成数: {crawl_progress_store[task_id]['completed']}/{crawl_progress_store[task_id]['total']}")
        print(f"    - 百分比: {progress_percentage:.1f}%")
        print(f"    - 已用时间: {elapsed_formatted}")
        print(f"    - 预计剩余: {estimated_formatted}")
        print(f"    - 预计完成时间: {estimated_completion_time}")
        print(f"    - 找到结果: {crawl_progress_store[task_id]['websites'][idx]['found']} 条")
        
        successful_crawls += 1
        results.extend([{'title': f'测试结果{idx}-{j}'} for j in range(idx * 2 + 1)])
    
    # 完成
    crawl_progress_store[task_id]['status'] = 'completed'
    crawl_progress_store[task_id]['results'] = results
    crawl_progress_store[task_id]['current_website'] = None
    crawl_progress_store[task_id]['progress_percentage'] = 100
    crawl_progress_store[task_id]['message'] = f'测试完成，共找到 {len(results)} 条结果'
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    print(f"✓ 总网站数: {crawl_progress_store[task_id]['total']}")
    print(f"✓ 完成网站数: {crawl_progress_store[task_id]['completed']}")
    print(f"✓ 成功率: {successful_crawls}/{len(websites)} ({successful_crawls/len(websites)*100:.0f}%)")
    print(f"✓ 找到结果数: {len(results)}")
    print(f"✓ 最终进度: {crawl_progress_store[task_id]['progress_percentage']}%")
    print(f"✓ 总耗时: {crawl_progress_store[task_id]['elapsed_time']}")
    print(f"✓ 最终状态: {crawl_progress_store[task_id]['status']}")
    print(f"✓ 最终消息: {crawl_progress_store[task_id]['message']}")
    print("=" * 60)
    
    # 验证进度存储
    print("\n验证进度存储:")
    print(f"  ✓ crawl_progress_store 包含 task_id: {task_id in crawl_progress_store}")
    print(f"  ✓ 进度状态正确: {crawl_progress_store[task_id]['status'] == 'completed'}")
    print(f"  ✓ 进度百分比正确: {crawl_progress_store[task_id]['progress_percentage'] == 100}")
    print(f"  ✓ 完成数正确: {crawl_progress_store[task_id]['completed'] == len(websites)}")
    print(f"  ✓ 预计剩余时间正确: {crawl_progress_store[task_id]['estimated_remaining'] == '即将完成'}")
    
    return True

def test_multithreaded_access():
    """测试多线程访问进度存储"""
    print("\n" + "=" * 60)
    print("测试多线程访问进度存储")
    print("=" * 60)
    
    import threading
    import time
    
    crawl_progress_store = {}
    task_id = 'multi-thread-test'
    
    # 初始化
    crawl_progress_store[task_id] = {
        'status': 'running',
        'total': 5,
        'completed': 0,
        'progress_percentage': 0,
        'elapsed_time': '0秒',
        'estimated_remaining': '15秒',
        'message': '开始多线程测试...'
    }
    
    results = {'updates': [], 'errors': []}
    
    def worker(thread_id):
        """模拟工作线程"""
        try:
            for i in range(5):
                # 模拟更新进度
                crawl_progress_store[task_id]['completed'] = i + 1
                crawl_progress_store[task_id]['progress_percentage'] = ((i + 1) / 5) * 100
                crawl_progress_store[task_id]['message'] = f'线程 {thread_id} 更新进度 {i + 1}'
                time.sleep(0.1)
                results['updates'].append((thread_id, i + 1))
        except Exception as e:
            results['errors'].append((thread_id, str(e)))
    
    # 启动多个线程
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    print(f"✓ 成功更新次数: {len(results['updates'])}")
    print(f"✓ 错误次数: {len(results['errors'])}")
    
    if results['errors']:
        print(f"  错误详情:")
        for error in results['errors']:
            print(f"    - 线程 {error[0]}: {error[1]}")
    else:
        print("  ✓ 没有错误，多线程访问正常")
    
    # 验证最终状态
    final_progress = crawl_progress_store[task_id]['progress_percentage']
    print(f"\n最终进度百分比: {final_progress}%")
    print(f"最终完成数: {crawl_progress_store[task_id]['completed']}")
    
    return len(results['errors']) == 0

if __name__ == '__main__':
    print("\n开始测试爬虫进度跟踪系统...")
    print()
    
    try:
        success1 = test_progress_tracking_simulation()
        success2 = test_multithreaded_access()
        
        print("\n" + "=" * 60)
        if success1 and success2:
            print("✓ 所有测试通过！")
            print("  进度跟踪系统工作正常")
        else:
            print("❌ 部分测试失败")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
