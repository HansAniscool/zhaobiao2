import pandas as pd
from ..models import GovernmentWebsite
from ..extensions import db
import re
from datetime import datetime
import os

class WebsiteExcelService:
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    
    def __init__(self):
        self.added = 0
        self.duplicates = 0
        self.errors = 0
        self.error_details = []
    
    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def is_valid_url(self, url):
        if not url:
            return False
        pattern = r'^https?://[^\s]+$|^www\.[^\s]+$'
        return bool(re.match(pattern, str(url).strip()))
    
    def is_duplicate(self, website):
        return GovernmentWebsite.query.filter_by(website=website).first() is not None
    
    def clean_text(self, text):
        if pd.isna(text):
            return None
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text if text else None
    
    def normalize_url(self, url):
        if not url:
            return None
        url = str(url).strip()
        if not url.startswith(('http://', 'https://', 'www.')):
            url = 'http://' + url
        url = url.rstrip('/')
        return url
    
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
        
        name_keywords = ['名称', 'name', '网站名称', '单位名称', '机构名称']
        url_keywords = ['网址', 'website', 'url', '链接', '地址', '网站地址']
        category_keywords = ['类别', 'category', '分类', '类型', '网站类型']
        region_keywords = ['地区', 'region', '区域', '省份', '城市', '所在地']
        level_keywords = ['级别', 'level', '行政级别', '层级']
        description_keywords = ['描述', 'description', '备注', '说明', '简介']
        
        for i, col in enumerate(df.columns):
            col_lower = col.lower()
            if col_lower in name_keywords:
                mapping['name'] = i
            elif col_lower in url_keywords:
                mapping['website'] = i
            elif col_lower in category_keywords:
                mapping['category'] = i
            elif col_lower in region_keywords:
                mapping['region'] = i
            elif col_lower in level_keywords:
                mapping['level'] = i
            elif col_lower in description_keywords:
                mapping['description'] = i
        
        return mapping if mapping else None
    
    def process_row(self, row, columns, mapping=None):
        name = None
        website = None
        
        if mapping and 'name' in mapping:
            name = self.clean_text(row.iloc[mapping['name']])
        else:
            for col in ['名称', 'name', '网站名称', '单位名称']:
                if col in columns:
                    name = self.clean_text(row[col])
                    break
        
        if not name:
            self.errors += 1
            self.error_details.append(f"缺少网站名称")
            return
        
        if mapping and 'website' in mapping:
            website = self.clean_text(row.iloc[mapping['website']])
        else:
            for col in ['网址', 'website', 'url', '链接', '地址']:
                if col in columns:
                    website = self.clean_text(row[col])
                    break
        
        if not website:
            self.errors += 1
            self.error_details.append(f"缺少网址: {name}")
            return
        
        website = self.normalize_url(website)
        
        if not self.is_valid_url(website):
            self.errors += 1
            self.error_details.append(f"无效网址格式: {website}")
            return
        
        if self.is_duplicate(website):
            self.duplicates += 1
            return
        
        category = None
        if mapping and 'category' in mapping:
            category = self.clean_text(row.iloc[mapping['category']])
        else:
            for col in ['类别', 'category', '分类', '类型']:
                if col in columns:
                    category = self.clean_text(row[col])
                    break
        
        region = None
        if mapping and 'region' in mapping:
            region = self.clean_text(row.iloc[mapping['region']])
        else:
            for col in ['地区', 'region', '区域', '省份', '城市']:
                if col in columns:
                    region = self.clean_text(row[col])
                    break
        
        level = None
        if mapping and 'level' in mapping:
            level = self.clean_text(row.iloc[mapping['level']])
        else:
            for col in ['级别', 'level', '行政级别', '层级']:
                if col in columns:
                    level = self.clean_text(row[col])
                    break
        
        description = None
        if mapping and 'description' in mapping:
            description = self.clean_text(row.iloc[mapping['description']])
        else:
            for col in ['描述', 'description', '备注', '说明', '简介']:
                if col in columns:
                    description = self.clean_text(row[col])
                    break
        
        website_obj = GovernmentWebsite(
            name=name,
            website=website,
            category=category,
            region=region,
            level=level,
            description=description
        )
        
        db.session.add(website_obj)
        self.added += 1
