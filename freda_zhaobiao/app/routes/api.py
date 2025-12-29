from flask import Blueprint, request, jsonify
from ..models import Tender, TenderFingerprint
from ..extensions import db
import hashlib
import re

bp = Blueprint('api', __name__)

def generate_fingerprint(title, organization, publish_date):
    content = f"{title}{organization}{publish_date}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def is_duplicate(fingerprint):
    return TenderFingerprint.query.filter_by(fingerprint=fingerprint).first() is not None

@bp.route('/api/tenders', methods=['GET'])
def get_tenders():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = request.args.get('q', '')
    sort = request.args.get('sort', 'date')
    
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
    
    if sort == 'date':
        base_query = base_query.order_by(Tender.publish_date.desc())
    
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'tenders': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })

@bp.route('/api/tenders/<int:tender_id>', methods=['GET'])
def get_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    return jsonify(tender.to_dict())

@bp.route('/api/tenders', methods=['POST'])
def create_tender():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    fingerprint = generate_fingerprint(
        data.get('title', ''),
        data.get('organization', ''),
        str(data.get('publish_date', ''))
    )
    
    if is_duplicate(fingerprint):
        return jsonify({'error': '招标信息已存在', 'duplicate': True}), 409
    
    try:
        from datetime import datetime, date
        if isinstance(data.get('publish_date'), str):
            publish_date = datetime.strptime(data['publish_date'], '%Y-%m-%d').date()
        else:
            publish_date = data.get('publish_date')
        
        tender = Tender(
            title=data.get('title'),
            publish_date=publish_date,
            organization=data.get('organization'),
            location=data.get('location'),
            summary=data.get('summary'),
            content=data.get('content'),
            source_url=data.get('source_url'),
            source_website=data.get('source_website'),
            category=data.get('category')
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        db.session.commit()
        
        return jsonify({'message': '创建成功', 'tender': tender.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tenders/<int:tender_id>', methods=['PUT'])
def update_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    try:
        if 'title' in data:
            tender.title = data['title']
        if 'summary' in data:
            tender.summary = data['summary']
        if 'content' in data:
            tender.content = data['content']
        if 'status' in data:
            tender.status = data['status']
        
        db.session.commit()
        
        return jsonify({'message': '更新成功', 'tender': tender.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tenders/<int:tender_id>', methods=['DELETE'])
def delete_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    
    try:
        TenderFingerprint.query.filter_by(tender_id=tender_id).delete()
        db.session.delete(tender)
        db.session.commit()
        
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/stats', methods=['GET'])
def get_stats():
    total = Tender.query.count()
    today = Tender.query.filter(Tender.publish_date >= db.func.current_date()).count()
    this_week = Tender.query.filter(
        Tender.publish_date >= db.func.date(db.func.now(), '-7 days')
    ).count()
    
    return jsonify({
        'total': total,
        'today': today,
        'this_week': this_week
    })

@bp.route('/crawl/tasks', methods=['GET'])
def get_all_crawl_tasks():
    from .tenders import crawl_progress_store
    import uuid
    
    tasks = []
    for task_id, progress in crawl_progress_store.items():
        task_info = {
            'task_id': task_id,
            'status': progress.get('status'),
            'total': progress.get('total', 0),
            'completed': progress.get('completed', 0),
            'message': progress.get('message', ''),
            'websites': progress.get('websites', []),
            'current_website': progress.get('current_website'),
            'start_time': progress.get('start_time'),
            'elapsed_time': progress.get('elapsed_time', ''),
            'estimated_remaining': progress.get('estimated_remaining'),
            'estimated_completion': progress.get('estimated_completion'),
            'progress_percentage': progress.get('progress_percentage', 0),
            'results_count': len(progress.get('results', []))
        }
        tasks.append(task_info)
    
    return jsonify({
        'count': len(tasks),
        'tasks': tasks
    })

@bp.route('/crawl/progress/<task_id>', methods=['GET'])
def get_crawl_progress(task_id):
    from .tenders import crawl_progress_store
    
    if task_id in crawl_progress_store:
        progress = crawl_progress_store[task_id]
        return jsonify({
            'task_id': task_id,
            'status': progress.get('status'),
            'total': progress.get('total', 0),
            'completed': progress.get('completed', 0),
            'message': progress.get('message', ''),
            'websites': progress.get('websites', []),
            'results': progress.get('results', []),
            'current_website': progress.get('current_website'),
            'start_time': progress.get('start_time'),
            'elapsed_time': progress.get('elapsed_time', ''),
            'estimated_remaining': progress.get('estimated_remaining'),
            'estimated_completion': progress.get('estimated_completion'),
            'progress_percentage': progress.get('progress_percentage', 0)
        })
    else:
        return jsonify({
            'task_id': task_id,
            'status': 'not_found',
            'message': '未找到该爬取任务'
        }), 404

@bp.route('/crawl/preview/<task_id>', methods=['GET'])
def preview_crawl_results(task_id):
    from .tenders import crawl_progress_store
    
    if task_id not in crawl_progress_store:
        return jsonify({
            'has_results': False,
            'html': '<div class="preview-empty"><div class="empty-icon">📭</div><p>未找到该爬取任务</p></div>'
        }), 404
    
    progress = crawl_progress_store[task_id]
    results = progress.get('results', [])
    
    if not results:
        return jsonify({
            'has_results': False,
            'html': '<div class="preview-empty"><div class="empty-icon">📭</div><p>暂无爬取结果</p></div>'
        })
    
    html = '<div class="preview-container">'
    html += f'<div class="preview-header"><h3>共 {len(results)} 条招标信息</h3></div>'
    html += '<div class="preview-list">'
    
    for i, result in enumerate(results[:20]):
        title = result.get('title', '未知标题')
        organization = result.get('organization', '未知单位')
        publish_date = result.get('publish_date', '未知日期')
        amount = result.get('amount', '未知金额')
        location = result.get('location', '')
        summary = result.get('summary', '')
        source_url = result.get('source_url', '')
        category = result.get('category', '')
        
        html += f'''
            <div class="preview-item">
                <div class="preview-item-header">
                    <div class="preview-title">{title}</div>
                    {f'<span class="preview-category">{category}</span>' if category else ''}
                </div>
                <div class="preview-item-meta">
                    <span>🏢 {organization}</span>
                    <span>📅 {publish_date}</span>
                    {f'<span>💰 {amount}</span>' if amount and amount != '未知金额' else ''}
                    {f'<span>📍 {location}</span>' if location else ''}
                </div>
                {f'<div class="preview-summary">{summary}</div>' if summary else ''}
                {f'<a href="{source_url}" target="_blank" class="preview-link">查看原文 →</a>' if source_url else ''}
            </div>
        '''
    
    if len(results) > 20:
        html += f'<div class="preview-more">... 还有 {len(results) - 20} 条结果未显示，点击下载查看全部</div>'
    
    html += '</div></div>'
    
    return jsonify({
        'has_results': True,
        'html': html,
        'total_count': len(results)
    })

@bp.route('/crawl/download/<task_id>', methods=['GET'])
def download_crawl_results(task_id):
    from .tenders import crawl_progress_store
    from flask import make_response
    import pandas as pd
    from io import BytesIO
    from datetime import datetime
    
    if task_id not in crawl_progress_store:
        return jsonify({'error': '未找到该爬取任务'}), 404
    
    progress = crawl_progress_store[task_id]
    results = progress.get('results', [])
    
    if not results:
        return jsonify({'error': '暂无爬取结果'}), 404
    
    df = pd.DataFrame(results)
    
    columns_order = ['title', 'publish_date', 'organization', 'amount', 'location', 'category', 'summary', 'source_url', 'source_website']
    available_columns = [col for col in columns_order if col in df.columns]
    df = df[available_columns]
    
    column_names = {
        'title': '招标标题',
        'publish_date': '发布日期',
        'organization': '招标单位',
        'amount': '项目金额',
        'location': '地区',
        'category': '分类',
        'summary': '摘要',
        'source_url': '原文链接',
        'source_website': '来源网站'
    }
    df = df.rename(columns=column_names)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='招标信息')
        
        workbook = writer.book
        worksheet = writer.sheets['招标信息']
        
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'招标信息_{task_id[:8]}_{timestamp}.xlsx'
    
    response = make_response(output.getvalue())
    response.mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
