from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..models import CrawlerTask, CrawlHistory
from ..extensions import db
from ..services.crawler_service import CrawlerService
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import uuid

bp = Blueprint('crawler', __name__)

scheduler = BackgroundScheduler()
scheduler.start()

def run_crawler_task(task_id):
    with scheduler.app.app_context():
        task = CrawlerTask.query.get(task_id)
        if task:
            service = CrawlerService()
            service.run_task(task)

@bp.route('/')
def crawler_index():
    tasks = CrawlerTask.query.order_by(CrawlerTask.created_at.desc()).all()
    running_tasks = [t for t in tasks if t.status == 'running']
    
    return render_template('crawler/index.html', tasks=tasks, running_count=len(running_tasks))

@bp.route('/create', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        name = request.form.get('name')
        website = request.form.get('website')
        keywords = request.form.get('keywords')
        category = request.form.get('category')
        region = request.form.get('region')
        crawl_interval = int(request.form.get('crawl_interval', 3600))
        
        task = CrawlerTask(
            name=name,
            website=website,
            keywords=keywords,
            category=category,
            region=region,
            crawl_interval=crawl_interval,
            created_by=1
        )
        
        db.session.add(task)
        db.session.commit()
        
        if 'start_now' in request.form:
            task.status = 'running'
            db.session.commit()
            scheduler.add_job(run_crawler_task, args=[task.id], id=str(task.id))
        
        flash('爬虫任务创建成功', 'success')
        return redirect(url_for('crawler.crawler_index'))
    
    return render_template('crawler/create.html')

@bp.route('/<int:task_id>')
def task_detail(task_id):
    task = CrawlerTask.query.get_or_404(task_id)
    histories = CrawlHistory.query.filter_by(task_id=task_id)\
        .order_by(CrawlHistory.start_time.desc()).limit(50).all()
    
    return render_template('crawler/detail.html', task=task, histories=histories)

@bp.route('/<int:task_id>/start', methods=['POST'])
def start_task(task_id):
    task = CrawlerTask.query.get_or_404(task_id)
    
    if task.status == 'running':
        return jsonify({'message': '任务已在运行中'}), 200
    
    task.status = 'running'
    db.session.commit()
    
    scheduler.add_job(run_crawler_task, args=[task.id], id=str(task.id), replace_existing=True)
    
    return jsonify({'message': '任务已启动'})

@bp.route('/<int:task_id>/stop', methods=['POST'])
def stop_task(task_id):
    task = CrawlerTask.query.get_or_404(task_id)
    
    task.status = 'stopped'
    db.session.commit()
    
    try:
        scheduler.remove_job(str(task_id))
    except:
        pass
    
    return jsonify({'message': '任务已停止'})

@bp.route('/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    task = CrawlerTask.query.get_or_404(task_id)
    
    try:
        scheduler.remove_job(str(task_id))
    except:
        pass
    
    CrawlHistory.query.filter_by(task_id=task_id).delete()
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': '任务已删除'})

@bp.route('/run-now/<int:task_id>', methods=['POST'])
def run_now(task_id):
    task = CrawlerTask.query.get_or_404(task_id)
    
    service = CrawlerService()
    service.run_task(task)
    
    flash('爬虫任务执行完成', 'success')
    return redirect(url_for('crawler.task_detail', task_id=task_id))

@bp.route('/history')
def crawl_history():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = CrawlHistory.query\
        .order_by(CrawlHistory.start_time.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('crawler/history.html', 
                         histories=pagination.items, 
                         pagination=pagination)
