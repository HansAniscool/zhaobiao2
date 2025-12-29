from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..models import Tender, TenderFingerprint, SystemLog, GovernmentWebsite
from ..extensions import db
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid

bp = Blueprint('admin', __name__)

@bp.route('/')
def admin_index():
    total_tenders = Tender.query.count()
    active_tenders = Tender.query.filter_by(status='active').count()
    today_tenders = Tender.query.filter(
        Tender.publish_date >= datetime.now().date()
    ).count()
    total_users = 1
    
    total_websites = GovernmentWebsite.query.count()
    active_websites = GovernmentWebsite.query.filter_by(status='active').count()
    
    recent_logs = SystemLog.query\
        .order_by(SystemLog.created_at.desc())\
        .limit(10).all()
    
    return render_template('admin/index.html',
                         total_tenders=total_tenders,
                         active_tenders=active_tenders,
                         today_tenders=today_tenders,
                         total_users=total_users,
                         total_websites=total_websites,
                         active_websites=active_websites,
                         recent_logs=recent_logs)

@bp.route('/tenders')
def manage_tenders():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')
    category = request.args.get('category')
    
    query = Tender.query
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    
    tenders = query.order_by(Tender.publish_date.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/tenders.html', 
                         pagination=tenders,
                         status=status,
                         category=category)

@bp.route('/tenders/export')
def export_tenders():
    status = request.args.get('status')
    category = request.args.get('category')
    format = request.args.get('format', 'excel')
    
    query = Tender.query
    
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    
    tenders = query.order_by(Tender.publish_date.desc()).all()
    
    from ..services.export_service import export_tenders as export_tenders_func
    return export_tenders_func(tenders, format)

@bp.route('/tenders/edit/<int:tender_id>')
def edit_tender(tender_id):
    tender = Tender.query.get_or_404(tender_id)
    return render_template('admin/edit_tender.html', tender=tender)

@bp.route('/logs')
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    level = request.args.get('level')
    
    query = SystemLog.query
    if level:
        query = query.filter_by(level=level)
    
    logs = query.order_by(SystemLog.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/logs.html', pagination=logs)

@bp.route('/websites', methods=['GET', 'POST'])
def manage_websites():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
                required_columns = ['name', 'url']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Excel文件缺少必要的列: {", ".join(missing_columns)}', 'danger')
                    return redirect(request.url)
                
                imported_count = 0
                updated_count = 0
                
                for _, row in df.iterrows():
                    if pd.isna(row.get('url')):
                        continue
                    
                    existing = GovernmentWebsite.query.filter_by(website=str(row['url']).strip()).first()
                    
                    if existing:
                        if 'name' in row and pd.notna(row['name']):
                            existing.name = str(row['name']).strip()
                        if 'category' in row and pd.notna(row.get('category')):
                            existing.category = str(row['category']).strip()
                        if 'description' in row and pd.notna(row.get('description')):
                            existing.description = str(row['description']).strip()
                        if 'status' in row and pd.notna(row.get('status')):
                            existing.status = str(row['status']).strip()
                        updated_count += 1
                    else:
                        website = GovernmentWebsite(
                            name=str(row.get('name', '')).strip() if pd.notna(row.get('name')) else '',
                            website=str(row['url']).strip(),
                            category=str(row.get('category', '')).strip() if pd.notna(row.get('category')) else '',
                            description=str(row.get('description', '')).strip() if pd.notna(row.get('description')) else '',
                            status=str(row.get('status', 'active')).strip() if pd.notna(row.get('status')) else 'active'
                        )
                        db.session.add(website)
                        imported_count += 1
                
                db.session.commit()
                flash(f'成功导入 {imported_count} 个网站，更新 {updated_count} 个网站', 'success')
                return redirect(url_for('admin.manage_websites'))
                
            except Exception as e:
                flash(f'处理文件时出错: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('只支持 .xlsx 和 .xls 格式的Excel文件', 'danger')
            return redirect(request.url)
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status')
    category = request.args.get('category')
    
    query = GovernmentWebsite.query
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.order_by(GovernmentWebsite.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/websites.html', pagination=pagination, websites=pagination.items)

@bp.route('/websites/delete/<int:website_id>')
def delete_website(website_id):
    website = GovernmentWebsite.query.get_or_404(website_id)
    db.session.delete(website)
    db.session.commit()
    flash('网站已删除', 'success')
    return redirect(url_for('admin.manage_websites'))

@bp.route('/websites/toggle/<int:website_id>')
def toggle_website(website_id):
    website = GovernmentWebsite.query.get_or_404(website_id)
    website.status = 'inactive' if website.status == 'active' else 'active'
    db.session.commit()
    flash(f'网站状态已更新: {website.status}', 'success')
    return redirect(url_for('admin.manage_websites'))

@bp.route('/websites/upload', methods=['GET', 'POST'])
def upload_websites():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
                required_columns = ['name', 'url']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Excel文件缺少必要的列: {", ".join(missing_columns)}', 'danger')
                    return redirect(request.url)
                
                imported_count = 0
                updated_count = 0
                
                for _, row in df.iterrows():
                    if pd.isna(row.get('url')):
                        continue
                    
                    website_url = str(row['url']).strip()
                    existing = GovernmentWebsite.query.filter_by(website=website_url).first()
                    
                    if existing:
                        if 'name' in row and pd.notna(row['name']):
                            existing.name = str(row['name']).strip()
                        if 'category' in row and pd.notna(row.get('category')):
                            existing.category = str(row['category']).strip()
                        if 'description' in row and pd.notna(row.get('description')):
                            existing.description = str(row['description']).strip()
                        if 'status' in row and pd.notna(row.get('status')):
                            existing.status = str(row['status']).strip()
                        updated_count += 1
                    else:
                        website = GovernmentWebsite(
                            name=str(row.get('name', '')).strip() if pd.notna(row.get('name')) else '',
                            website=website_url,
                            category=str(row.get('category', '')).strip() if pd.notna(row.get('category')) else '',
                            description=str(row.get('description', '')).strip() if pd.notna(row.get('description')) else '',
                            status=str(row.get('status', 'active')).strip() if pd.notna(row.get('status')) else 'active'
                        )
                        db.session.add(website)
                        imported_count += 1
                
                db.session.commit()
                flash(f'成功导入 {imported_count} 个网站，更新 {updated_count} 个网站', 'success')
                return redirect(url_for('admin.manage_websites'))
                
            except Exception as e:
                flash(f'处理文件时出错: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('只支持 .xlsx 和 .xls 格式的Excel文件', 'danger')
            return redirect(request.url)
    
    return render_template('admin/upload_websites.html')

@bp.route('/api/websites')
def api_websites():
    websites = GovernmentWebsite.query.filter_by(status='active').all()
    return jsonify([{
        'id': w.id,
        'name': w.name,
        'url': w.website,
        'category': w.category
    } for w in websites])

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
                required_columns = ['title', 'url']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Excel文件缺少必要的列: {", ".join(missing_columns)}', 'danger')
                    return redirect(request.url)
                
                imported_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    if pd.isna(row.get('url')):
                        skipped_count += 1
                        continue
                    
                    source_url = str(row['url']).strip()
                    existing_url = Tender.query.filter_by(source_url=source_url).first()
                    
                    if existing_url:
                        skipped_count += 1
                        continue
                    
                    tender = Tender(
                        title=str(row['title'])[:500] if pd.notna(row['title']) else '无标题',
                        source_url=source_url,
                        organization=str(row.get('organization', ''))[:200] if pd.notna(row.get('organization')) else None,
                        category=str(row.get('category', ''))[:50] if pd.notna(row.get('category')) else None,
                        summary=str(row.get('summary', ''))[:2000] if pd.notna(row.get('summary')) else None,
                        content=str(row.get('content', '')) if pd.notna(row.get('content')) else None,
                        status='active'
                    )
                    
                    if pd.notna(row.get('publish_date')):
                        try:
                            if isinstance(row['publish_date'], str):
                                tender.publish_date = datetime.strptime(row['publish_date'], '%Y-%m-%d').date()
                            else:
                                tender.publish_date = row['publish_date'].date()
                        except:
                            tender.publish_date = datetime.now().date()
                    else:
                        tender.publish_date = datetime.now().date()
                    
                    db.session.add(tender)
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
                        db.session.commit()
                
                db.session.commit()
                flash(f'成功导入 {imported_count} 条招标信息，跳过 {skipped_count} 条重复数据', 'success')
                return redirect(url_for('admin.manage_tenders'))
                
            except Exception as e:
                flash(f'处理文件时出错: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('只支持 .xlsx 和 .xls 格式的Excel文件', 'danger')
            return redirect(request.url)
    
    return render_template('admin/upload.html')
