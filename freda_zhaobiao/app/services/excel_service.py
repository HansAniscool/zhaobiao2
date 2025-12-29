import pandas as pd
from ..models import Tender, TenderFingerprint
from ..extensions import db
import hashlib
import re
from datetime import datetime
import os

class ExcelService:
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    
    def __init__(self):
        self.added = 0
        self.duplicates = 0
        self.errors = 0
        self.error_details = []
    
    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def generate_fingerprint(self, title, organization, publish_date):
        content = f"{title}{organization}{str(publish_date)}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, fingerprint):
        return TenderFingerprint.query.filter_by(fingerprint=fingerprint).first() is not None
    
    def parse_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, str):
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%Y年%m月%d日']:
                try:
                    return datetime.strptime(date_value.strip(), fmt).date()
                except ValueError:
                    continue
        return None
    
    def clean_text(self, text):
        if pd.isna(text):
            return None
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text if text else None
    
    def import_from_file(self, filepath):
        self.added = 0
        self.duplicates = 0
        self.errors = 0
        self.error_details = []
        
        try:
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext == '.csv':
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                df = pd.read_excel(filepath)
            
            column_mapping = self.detect_columns(df)
            
            for idx, row in df.iterrows():
                try:
                    self.process_row(row, df.columns.tolist(), column_mapping)
                except Exception as e:
                    self.errors += 1
                    self.error_details.append(f"行 {idx+2}: {str(e)}")
            
            db.session.commit()
            
        except Exception as e:
            self.errors += 1
            self.error_details.append(f"文件读取错误: {str(e)}")
        
        return {
            'added': self.added,
            'duplicates': self.duplicates,
            'errors': self.errors,
            'error_details': self.error_details
        }
    
    def detect_columns(self, df):
        mapping = {}
        columns = [c.lower() for c in df.columns]
        
        title_keywords = ['标题', 'title', '名称', '项目名称', '招标名称']
        date_keywords = ['日期', 'date', '发布时间', '发布日', '发布日期']
        org_keywords = ['单位', 'organization', '发布单位', '招标人', '采购人']
        summary_keywords = ['摘要', 'summary', '简介', '概述', '内容摘要']
        url_keywords = ['链接', 'link', 'url', '网址', '链接地址']
        category_keywords = ['类别', 'category', '分类', '类型']
        
        for i, col in enumerate(df.columns):
            col_lower = col.lower()
            if col_lower in title_keywords:
                mapping['title'] = i
            elif col_lower in date_keywords:
                mapping['publish_date'] = i
            elif col_lower in org_keywords:
                mapping['organization'] = i
            elif col_lower in summary_keywords:
                mapping['summary'] = i
            elif col_lower in url_keywords:
                mapping['source_url'] = i
            elif col_lower in category_keywords:
                mapping['category'] = i
        
        return mapping if mapping else None
    
    def process_row(self, row, columns, mapping=None):
        title = None
        
        if mapping and 'title' in mapping:
            title = self.clean_text(row.iloc[mapping['title']])
        else:
            for col in ['标题', 'title', '项目名称', '招标名称']:
                if col in columns:
                    title = self.clean_text(row[col])
                    break
        
        if not title:
            return
        
        if mapping and 'publish_date' in mapping:
            publish_date = self.parse_date(row.iloc[mapping['publish_date']])
        else:
            publish_date = None
            for col in ['日期', 'date', '发布时间', '发布日期']:
                if col in columns:
                    publish_date = self.parse_date(row[col])
                    break
        
        organization = None
        if mapping and 'organization' in mapping:
            organization = self.clean_text(row.iloc[mapping['organization']])
        else:
            for col in ['单位', 'organization', '发布单位', '招标人']:
                if col in columns:
                    organization = self.clean_text(row[col])
                    break
        
        summary = None
        if mapping and 'summary' in mapping:
            summary = self.clean_text(row.iloc[mapping['summary']])
        else:
            for col in ['摘要', 'summary', '简介', '概述']:
                if col in columns:
                    summary = self.clean_text(row[col])
                    break
        
        source_url = None
        if mapping and 'source_url' in mapping:
            source_url = self.clean_text(row.iloc[mapping['source_url']])
        else:
            for col in ['链接', 'link', 'url', '网址']:
                if col in columns:
                    source_url = self.clean_text(row[col])
                    break
        
        category = None
        if mapping and 'category' in mapping:
            category = self.clean_text(row.iloc[mapping['category']])
        else:
            for col in ['类别', 'category', '分类', '类型']:
                if col in columns:
                    category = self.clean_text(row[col])
                    break
        
        fingerprint = self.generate_fingerprint(title, organization, publish_date)
        
        if self.is_duplicate(fingerprint):
            self.duplicates += 1
            return
        
        tender = Tender(
            title=title,
            publish_date=publish_date,
            organization=organization,
            summary=summary,
            source_url=source_url,
            category=category
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        self.added += 1
