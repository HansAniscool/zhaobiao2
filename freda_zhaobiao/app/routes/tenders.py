from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from ..models import Tender, TenderFingerprint, Favorite, SearchHistory, GovernmentWebsite
from ..extensions import db
from ..utils import save_search_history, get_search_history
from ..services.crawler_service import CrawlerService
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
import logging
import uuid
from threading import Thread
from flask import Flask
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

crawl_progress_store = {}

def generate_fingerprint(title, publish_date, source_url):
    """生成招标信息的唯一指纹"""
    content = f"{title or ''}_{publish_date or ''}_{source_url or ''}"
    return generate_password_hash(content)[:64]

def save_tenders_to_db(results, query, category=None):
    """
    将爬取的招标信息保存到数据库
    返回: 保存成功的数量
    """
    saved_count = 0
    skipped_count = 0
    
    for item in results:
        try:
            title = item.get('title', '').strip()
            if not title or len(title) < 5:
                continue
            
            fingerprint = generate_fingerprint(
                item.get('title'),
                str(item.get('publish_date', '')),
                item.get('source_url', '')
            )
            
            existing = TenderFingerprint.query.filter_by(fingerprint=fingerprint).first()
            if existing:
                skipped_count += 1
                continue
            
            publish_date = item.get('publish_date')
            if isinstance(publish_date, str):
                try:
                    publish_date = datetime.strptime(publish_date, '%Y-%m-%d').date()
                except ValueError:
                    publish_date = datetime.now().date()
            elif not publish_date:
                publish_date = datetime.now().date()
            
            tender = Tender(
                title=title,
                publish_date=publish_date,
                organization=item.get('organization'),
                location=item.get('location'),
                summary=item.get('summary', '')[:500],
                content=item.get('content'),
                source_url=item.get('source_url'),
                source_website=item.get('source_website'),
                category=item.get('category') or category or 'other',
                status='active',
                view_count=0
            )
            
            db.session.add(tender)
            db.session.flush()
            
            tender_fingerprint = TenderFingerprint(
                tender_id=tender.id,
                fingerprint=fingerprint
            )
            db.session.add(tender_fingerprint)
            
            saved_count += 1
            
        except Exception as e:
            logger.error(f"保存招标信息失败: {str(e)}")
            continue
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"提交数据库事务失败: {str(e)}")
    
    return saved_count, skipped_count

def start_crawl_task(task_id, query, category):
    """
    在后台线程中执行爬取任务并更新进度
    使用传入的task_id确保与主线程中的进度存储一致
    """
    app = current_app._get_current_object()
    with app.app_context():
        try:
            from ..models import GovernmentWebsite
            
            websites = GovernmentWebsite.query.filter_by(status='active').all()
            
            if not websites:
                crawl_progress_store[task_id] = {
                    'status': 'completed',
                    'total': 0,
                    'completed': 0,
                    'results': [],
                    'message': '没有找到可用的政府网站进行爬取',
                    'current_website': None,
                    'start_time': datetime.now().isoformat(),
                    'start_datetime': datetime.now(),
                    'estimated_completion': None,
                    'elapsed_time': '0秒',
                    'estimated_remaining': None,
                    'progress_percentage': 0
                }
                return
            
            crawl_progress_store[task_id].update({
                'status': 'running',
                'total': len(websites),
                'completed': 0,
                'results': [],
                'message': f'开始爬取 {len(websites)} 个政府网站...',
                'websites': [{'name': w.name, 'url': w.website, 'status': 'pending'} for w in websites],
                'current_website': None,
                'start_time': datetime.now().isoformat(),
                'start_datetime': datetime.now(),
                'estimated_completion': None,
                'elapsed_time': '0秒',
                'estimated_remaining': len(websites) * 3,
                'progress_percentage': 0
            })
            
            results = []
            start_time = datetime.now()
            successful_crawls = 0
            failed_crawls = 0
            
            for idx, website in enumerate(websites):
                website_start_time = datetime.now()
                crawl_progress_store[task_id]['websites'][idx]['status'] = 'running'
                crawl_progress_store[task_id]['websites'][idx]['started_at'] = website_start_time.isoformat()
                crawl_progress_store[task_id]['current_website'] = {
                    'name': website.name,
                    'url': website.website,
                    'progress': idx + 1,
                    'total': len(websites),
                    'start_time': website_start_time.isoformat(),
                    'start_datetime': website_start_time.isoformat()
                }
                crawl_progress_store[task_id]['message'] = f'正在爬取: {website.name} ({idx + 1}/{len(websites)})'
                
                try:
                    website_results = crawl_single_website_fast(website, query, category)
                    crawl_progress_store[task_id]['websites'][idx]['status'] = 'completed'
                    crawl_progress_store[task_id]['websites'][idx]['completed_at'] = datetime.now().isoformat()
                    crawl_progress_store[task_id]['websites'][idx]['found'] = len(website_results)
                    crawl_progress_store[task_id]['websites'][idx]['results'] = website_results[:5]
                    crawl_progress_store[task_id]['websites'][idx]['duration'] = round((datetime.now() - website_start_time).total_seconds(), 1)
                    successful_crawls += 1
                    
                    results.extend(website_results)
                    
                except Exception as e:
                    crawl_progress_store[task_id]['websites'][idx]['status'] = 'failed'
                    crawl_progress_store[task_id]['websites'][idx]['error'] = str(e)[:100]
                    crawl_progress_store[task_id]['websites'][idx]['completed_at'] = datetime.now().isoformat()
                    crawl_progress_store[task_id]['websites'][idx]['duration'] = round((datetime.now() - website_start_time).total_seconds(), 1)
                    failed_crawls += 1
                    logger.error(f"爬取网站 {website.name} 失败: {str(e)}")
                
                crawl_progress_store[task_id]['completed'] = idx + 1
                
                elapsed_seconds = int((datetime.now() - start_time).total_seconds())
                minutes = elapsed_seconds // 60
                seconds = elapsed_seconds % 60
                elapsed_formatted = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
                
                progress_percentage = ((idx + 1) / len(websites)) * 100
                
                remaining_websites = len(websites) - idx - 1
                avg_time_per_website = (datetime.now() - start_time).total_seconds() / (idx + 1) if idx > 0 else 3
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
                crawl_progress_store[task_id]['estimated_remaining_seconds'] = estimated_remaining_seconds
                crawl_progress_store[task_id]['estimated_completion'] = estimated_completion_time
                crawl_progress_store[task_id]['progress_percentage'] = round(progress_percentage, 1)
                crawl_progress_store[task_id]['message'] = f'已完成 {idx + 1}/{len(websites)} 个网站 (成功{successful_crawls}, 失败{failed_crawls})，预计还需 {estimated_formatted}'
            
            crawl_progress_store[task_id]['status'] = 'completed'
            crawl_progress_store[task_id]['results'] = results
            crawl_progress_store[task_id]['current_website'] = None
            crawl_progress_store[task_id]['estimated_completion'] = datetime.now().strftime('%H:%M:%S')
            crawl_progress_store[task_id]['progress_percentage'] = 100
            crawl_progress_store[task_id]['estimated_remaining'] = '已完成'
            
            saved_count, skipped_count = save_tenders_to_db(results, query, category)
            crawl_progress_store[task_id]['saved_count'] = saved_count
            crawl_progress_store[task_id]['skipped_count'] = skipped_count
            crawl_progress_store[task_id]['total_in_db'] = Tender.query.count()
            
            history_id = crawl_progress_store[task_id].get('history_id')
            if history_id:
                total_results = saved_count + skipped_count
                update_search_history(history_id, total_results)
            
            crawl_progress_store[task_id]['message'] = f'爬取完成，共找到 {len(results)} 条招标信息，保存 {saved_count} 条 (重复跳过 {skipped_count} 条)，耗时 {crawl_progress_store[task_id]["elapsed_time"]} (成功{successful_crawls}, 失败{failed_crawls}个网站)'
            
        except Exception as e:
            logger.error(f"爬取任务出错: {str(e)}")
            crawl_progress_store[task_id] = {
                'status': 'failed',
                'error': str(e),
                'message': f'爬取出错: {str(e)}',
                'current_website': None,
                'progress_percentage': 0
            }

def crawl_websites_for_query(query, category=None):
    """
    从政府网站爬取与搜索关键词相关的招标信息
    返回: list of dict containing tender info for display
    """
    try:
        websites = GovernmentWebsite.query.filter_by(status='active').all()
        
        if not websites:
            flash('没有找到可用的政府网站进行爬取', 'warning')
            return []
        
        results = []
        
        for website in websites:
            try:
                website_results = crawl_single_website(website, query, category)
                results.extend(website_results)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"爬取网站 {website.name} 失败: {str(e)}")
                continue
        
        return results
        
    except Exception as e:
        logger.error(f"爬取过程出错: {str(e)}")
        flash(f'爬取出错: {str(e)}', 'error')
        return []

def crawl_single_website(website, query, category=None):
    """
    爬取单个政府网站获取招标信息
    """
    results = []
    start_time = time.time()
    timeout_seconds = 10
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'close',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        base_url = website.website
        search_urls = generate_search_urls(base_url, query)
        logger.info(f"爬取 {website.name}: 生成URL列表 {search_urls}")
        
        for search_url in search_urls:
            try:
                if time.time() - start_time > timeout_seconds:
                    logger.warning(f"爬取超时: {website.name}")
                    break
                    
                response = session.get(search_url, timeout=5, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = extract_tender_items(soup, base_url)
                    
                    for item in items:
                        if category and item.get('category') != category:
                            continue
                        if query.lower() not in item.get('title', '').lower():
                            continue
                        item['source_website'] = website.name
                        item['website_url'] = website.website
                        results.append(item)
                    
                    break
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时: {search_url}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接失败: {search_url}, 错误: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"请求异常 {search_url}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"爬取网站 {website.name} 时出错: {str(e)}")
    
    return results

def crawl_single_website_fast(website, query, category=None):
    """
    快速爬取单个政府网站获取招标信息（优化版）
    减少超时时间，快速失败，继续下一个网站
    """
    results = []
    start_time = time.time()
    max_time_per_website = 5
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'close',
            'Cache-Control': 'no-cache',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        base_url = website.website
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        
        search_urls = generate_search_urls(base_url, query)
        
        for search_url in search_urls:
            elapsed = time.time() - start_time
            if elapsed > max_time_per_website:
                break
            
            try:
                response = session.get(search_url, timeout=3, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = extract_tender_items(soup, base_url)
                    
                    for item in items:
                        title = item.get('title', '')
                        if query and query.lower() not in title.lower():
                            continue
                        item['source_website'] = website.name
                        item['website_url'] = website.website
                        results.append(item)
                    
                    if results:
                        break
                    
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                continue
            except requests.exceptions.SSLError:
                continue
            except Exception:
                continue
        
    except Exception:
        pass
    
    return results

def generate_search_urls(base_url, query):
    """
    生成搜索URL列表（优化版：减少URL数量，提高效率）
    """
    urls = []
    
    if not base_url:
        return urls
    
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    
    query_encoded = requests.utils.quote(query)
    
    if 'ccgp.gov.cn' in base_url or 'ccgp-' in base_url:
        urls.append(f"{base_url}/search?keyword={query_encoded}")
    elif 'chinabidding.cn' in base_url:
        urls.append(f"{base_url}/search?keyword={query_encoded}")
    elif 'cpir.cn' in base_url:
        urls.append(f"{base_url}?keywords={query_encoded}")
    elif 'gov.cn' in base_url:
        urls.append(f"{base_url}/search?q={query_encoded}")
    else:
        urls.append(base_url)
    
    return urls[:3]

def extract_tender_items(soup, base_url):
    """
    从页面中提取招标信息项
    """
    items = []
    
    selectors = [
        ('.news-list li', 'a', '.date, .time, span:last-child'),
        ('.bid-list li', 'a', '.date, .time'),
        ('.tender-list li', 'a', '.date, .time'),
        ('.list-box li', 'a', '.date, .time'),
        ('table tr', 'a', 'td:last-child, td:nth-child(2)'),
        ('.article-list li', 'a', '.date'),
        ('ul li', 'a', None),
    ]
    
    for selector_tuple in selectors:
        container_sel, link_sel, date_sel = selector_tuple
        containers = soup.select(container_sel)
        
        for container in containers:
            try:
                link_elem = container.select_one(link_sel)
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = requests.compat.urljoin(base_url, link)
                
                date_text = None
                if date_sel:
                    date_elem = container.select_one(date_sel)
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                
                publish_date = parse_date_string(date_text)
                
                summary = container.get_text(strip=True)
                if len(summary) > 200:
                    summary = summary[:200] + '...'
                
                item = {
                    'title': title,
                    'publish_date': publish_date,
                    'source_url': link,
                    'summary': summary,
                    'category': extract_category(container),
                }
                
                items.append(item)
                
            except Exception as e:
                continue
    
    return items

def parse_date_string(date_str):
    """
    解析日期字符串
    """
    if not date_str:
        return datetime.now().date()
    
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y年%m月%d日',
        '%Y.%m.%d',
        '%m-%d',
        '%m/%d',
    ]
    
    date_str = date_str.strip()
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if fmt in ['%m-%d', '%m/%d']:
                return datetime.now().replace(month=parsed.month, day=parsed.day).date()
            return parsed.date()
        except ValueError:
            continue
    
    return datetime.now().date()

def extract_category(container):
    """
    从容器中提取分类信息
    """
    category_keywords = {
        '工程': 'engineering',
        '货物': 'goods', 
        '服务': 'services',
        '采购': 'procurement',
        '招标': 'bidding',
        '中标': 'result',
        '变更': 'modification',
    }
    
    text = container.get_text().lower()
    
    for keyword, category in category_keywords.items():
        if keyword in text:
            return category
    
    return 'other'

bp = Blueprint('tenders', __name__)

@bp.route('/')
def index():
    latest_tenders = Tender.query.filter(Tender.status == 'active')\
        .order_by(Tender.publish_date.desc())\
        .limit(10).all()
    
    recent_history = SearchHistory.query.order_by(
        SearchHistory.created_at.desc()
    ).limit(5).all()
    
    return render_template('index.html', tenders=latest_tenders, recent_history=recent_history)

@bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    sort = request.args.get('sort', 'date')
    category = request.args.get('category', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    crawl = request.args.get('crawl', 'true').lower() == 'true'
    
    if not query:
        return render_template('search.html', tenders=[], query='')
    
    history_id = save_search_history(query, date_from, date_to, category, result_count=0)
    
    base_query = Tender.query.filter(Tender.status == 'active')
    
    if query:
        search_pattern = f'%{query}%'
        base_query = base_query.filter(
            db.or_(
                Tender.title.ilike(search_pattern),
                Tender.summary.ilike(search_pattern),
                Tender.organization.ilike(search_pattern)
            )
        )
    
    if category:
        base_query = base_query.filter(Tender.category == category)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            base_query = base_query.filter(Tender.publish_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            base_query = base_query.filter(Tender.publish_date <= date_to_obj)
        except ValueError:
            pass
    
    if sort == 'date':
        base_query = base_query.order_by(Tender.publish_date.desc())
    elif sort == 'relevance':
        pass
    
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    
    if page == 1 and crawl:
        task_id = str(uuid.uuid4())
        
        websites = GovernmentWebsite.query.filter_by(status='active').all()
        total_websites = len(websites)
        
        crawl_progress_store[task_id] = {
            'status': 'running',
            'total': total_websites,
            'completed': 0,
            'results': [],
            'message': '正在启动爬取任务...',
            'websites': [{'name': w.name, 'url': w.website, 'status': 'pending'} for w in websites] if websites else [],
            'current_website': None,
            'start_time': datetime.now().isoformat(),
            'start_datetime': datetime.now(),
            'estimated_completion': None,
            'elapsed_time': '0秒',
            'estimated_remaining': total_websites * 3 if total_websites > 0 else None,
            'progress_percentage': 0,
            'history_id': history_id
        }
        
        app = current_app._get_current_object()
        def run_crawl_with_context():
            with app.app_context():
                start_crawl_task(task_id, query, category)
        
        Thread(target=run_crawl_with_context).start()
        
        return render_template('search.html',
                             tenders=[],
                             pagination=None,
                             query=query,
                             sort=sort,
                             category=category,
                             date_from=date_from,
                             date_to=date_to,
                             task_id=task_id,
                             crawling=True)
    
    update_search_history(history_id, pagination.total)
    
    return render_template('search.html', 
                         tenders=pagination.items, 
                         pagination=pagination,
                         query=query,
                         sort=sort,
                         category=category,
                         date_from=date_from,
                         date_to=date_to,
                         crawled=False)

@bp.route('/tender/<int:tender_id>')
def tender_detail(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    tender.view_count += 1
    db.session.commit()
    
    is_favorite = False
    return render_template('tender_detail.html', tender=tender, is_favorite=is_favorite)

@bp.route('/favorite/<int:tender_id>', methods=['POST'])
def add_favorite(tender_id):
    flash('收藏功能需要登录后使用', 'info')
    return redirect(url_for('tenders.tender_detail', tender_id=tender_id))

@bp.route('/favorites')
def favorites():
    return render_template('favorites.html', favorites=[])

@bp.route('/history')
def search_history():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = SearchHistory.query
    histories = query.order_by(SearchHistory.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('history.html', histories=histories)

@bp.route('/history/delete/<int:history_id>', methods=['POST'])
def delete_history(history_id):
    from ..utils import delete_search_history
    success = delete_search_history(history_id)
    if success:
        flash('已删除该搜索记录', 'success')
    else:
        flash('删除失败，记录不存在', 'error')
    return redirect(url_for('tenders.history'))

@bp.route('/history/clear', methods=['POST'])
def clear_history():
    from ..utils import clear_search_history
    success = clear_search_history()
    if success:
        flash('已清空所有搜索记录', 'success')
    else:
        flash('清空失败', 'error')
    return redirect(url_for('tenders.history'))

@bp.route('/monitor')
def monitor():
    return render_template('monitor.html')

@bp.route('/save-crawl-results', methods=['POST'])
def save_crawl_results():
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id or task_id not in crawl_progress_store:
            return jsonify({
                'status': 'error',
                'message': '任务不存在或已过期'
            }), 404
        
        task_data = crawl_progress_store[task_id]
        results = task_data.get('results', [])
        
        if not results:
            return jsonify({
                'status': 'error',
                'message': '没有可保存的结果'
            }), 400
        
        query = task_data.get('query', '')
        category = task_data.get('category', None)
        
        saved_count, skipped_count = save_tenders_to_db(results, query, category)
        total_in_db = Tender.query.count()
        
        task_data['saved_count'] = saved_count
        task_data['skipped_count'] = skipped_count
        task_data['total_in_db'] = total_in_db
        
        return jsonify({
            'status': 'success',
            'message': f'成功保存 {saved_count} 条记录，跳过 {skipped_count} 条重复记录',
            'saved_count': saved_count,
            'skipped_count': skipped_count,
            'total_in_db': total_in_db
        })
        
    except Exception as e:
        logger.error(f"保存爬取结果失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'保存失败: {str(e)}'
        }), 500

@bp.route('/export')
def export_data():
    query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    format = request.args.get('format', 'excel')
    
    base_query = Tender.query.filter(Tender.status == 'active')
    
    if query:
        search_pattern = f'%{query}%'
        base_query = base_query.filter(
            db.or_(
                Tender.title.ilike(search_pattern),
                Tender.summary.ilike(search_pattern)
            )
        )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            base_query = base_query.filter(Tender.publish_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            base_query = base_query.filter(Tender.publish_date <= date_to_obj)
        except ValueError:
            pass
    
    tenders = base_query.order_by(Tender.publish_date.desc()).all()
    
    from services.export_service import export_tenders
    return export_tenders(tenders, format)
