import requests
from bs4 import BeautifulSoup
from ..models import Tender, TenderFingerprint, CrawlHistory
from ..extensions import db
import hashlib
import re
from datetime import datetime, date
import time
import random
from urllib.parse import urljoin, urlparse
import logging

class CrawlerService:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.request_delay = 2
        self.max_retry = 3
        self.timeout = 30
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        self.added = 0
        self.updated = 0
        self.skipped = 0
        self.errors = []
    
    def generate_fingerprint(self, title, organization, publish_date):
        content = f"{title}{organization}{str(publish_date)}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, fingerprint):
        return TenderFingerprint.query.filter_by(fingerprint=fingerprint).first() is not None
    
    def parse_date(self, date_str):
        if not date_str:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日',
            '%Y.%m.%d',
            '%d/%m/%Y',
            '%m/%d/%Y'
        ]
        
        date_str = str(date_str).strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def clean_text(self, text):
        if not text:
            return None
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text if text else None
    
    def crawl_website(self, website, keywords=None, category=None, region=None):
        self.added = 0
        self.updated = 0
        self.skipped = 0
        self.errors = []
        
        parsed_url = urlparse(website)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if 'chinabidding.cn' in parsed_url.netloc:
            self._crawl_chinabidding(website, keywords)
        elif 'ccgp.gov.cn' in parsed_url.netloc:
            self._crawl_ccgp(website, keywords)
        elif 'cpir.cn' in parsed_url.netloc:
            self._crawl_cpir(website, keywords)
        else:
            self._crawl_generic(website, keywords)
        
        return {
            'added': self.added,
            'updated': self.updated,
            'skipped': self.skipped,
            'errors': self.errors
        }
    
    def _crawl_chinabidding(self, url, keywords):
        search_url = url
        if keywords:
            search_url = f"{url}/search?keyword={keywords}"
        
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(search_url, timeout=self.timeout)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = soup.select('.news-list li, .bid-list li, .table-list tr')
                    
                    for item in items:
                        try:
                            self._parse_chinabidding_item(item, base_url)
                        except Exception as e:
                            self.errors.append(str(e))
                    
                    break
            except Exception as e:
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(1, 3))
                else:
                    self.errors.append(f"请求失败: {str(e)}")
        
        time.sleep(self.request_delay)
    
    def _crawl_ccgp(self, url, keywords):
        search_url = url
        if keywords:
            search_url = f"{url}?keyword={keywords}"
        
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(search_url, timeout=self.timeout)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = soup.select('.list-box li, .news-list li, table tr')
                    
                    for item in items:
                        try:
                            self._parse_ccgp_item(item, base_url)
                        except Exception as e:
                            self.errors.append(str(e))
                    
                    break
            except Exception as e:
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(1, 3))
                else:
                    self.errors.append(f"请求失败: {str(e)}")
        
        time.sleep(self.request_delay)
    
    def _crawl_cpir(self, url, keywords):
        search_url = url
        if keywords:
            search_url = f"{url}?keywords={keywords}"
        
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(search_url, timeout=self.timeout)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = soup.select('.zbyc-article-list li, .tender-list li, .news-list li')
                    
                    for item in items:
                        try:
                            self._parse_cpir_item(item, base_url)
                        except Exception as e:
                            self.errors.append(str(e))
                    
                    break
            except Exception as e:
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(1, 3))
                else:
                    self.errors.append(f"请求失败: {str(e)}")
        
        time.sleep(self.request_delay)
    
    def _crawl_generic(self, url, keywords):
        for attempt in range(self.max_retry):
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    
                    for tag in soup.find_all(['li', 'tr'], class_=re.compile(r'news|tender|bid|article', re.I)):
                        try:
                            self._parse_generic_item(tag, url)
                        except Exception as e:
                            self.errors.append(str(e))
                    
                    break
            except Exception as e:
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(1, 3))
                else:
                    self.errors.append(f"请求失败: {str(e)}")
        
        time.sleep(self.request_delay)
    
    def _parse_chinabidding_item(self, item, base_url):
        title_elem = item.select_one('a, .title')
        date_elem = item.select_one('.date, .time, span:last-child')
        
        if not title_elem:
            return
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return
        
        link = title_elem.get('href', '')
        if link and not link.startswith('http'):
            link = urljoin(base_url, link)
        
        publish_date = self.parse_date(date_elem.get_text() if date_elem else None)
        
        fingerprint = self.generate_fingerprint(title, None, publish_date)
        
        if self.is_duplicate(fingerprint):
            self.skipped += 1
            return
        
        tender = Tender(
            title=title,
            publish_date=publish_date,
            source_url=link,
            source_website='中国采购与招标网',
            summary=self.clean_text(item.get_text()[:200])
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        self.added += 1
    
    def _parse_ccgp_item(self, item, base_url):
        title_elem = item.select_one('a, .title')
        date_elem = item.select_one('.date, .time, span')
        
        if not title_elem:
            return
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return
        
        link = title_elem.get('href', '')
        if link and not link.startswith('http'):
            link = urljoin(base_url, link)
        
        publish_date = self.parse_date(date_elem.get_text() if date_elem else None)
        
        fingerprint = self.generate_fingerprint(title, None, publish_date)
        
        if self.is_duplicate(fingerprint):
            self.skipped += 1
            return
        
        tender = Tender(
            title=title,
            publish_date=publish_date,
            source_url=link,
            source_website='中国政府采购网',
            summary=self.clean_text(item.get_text()[:200])
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        self.added += 1
    
    def _parse_cpir_item(self, item, base_url):
        title_elem = item.select_one('a')
        
        if not title_elem:
            return
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return
        
        link = title_elem.get('href', '')
        if link and not link.startswith('http'):
            link = urljoin(base_url, link)
        
        fingerprint = self.generate_fingerprint(title, None, date.today())
        
        if self.is_duplicate(fingerprint):
            self.skipped += 1
            return
        
        tender = Tender(
            title=title,
            publish_date=date.today(),
            source_url=link,
            source_website='中国招标投标公共服务平台',
            summary=self.clean_text(item.get_text()[:200])
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        self.added += 1
    
    def _parse_generic_item(self, item, base_url):
        title_elem = item.select_one('a')
        
        if not title_elem:
            return
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return
        
        link = title_elem.get('href', '')
        if link and not link.startswith('http'):
            link = urljoin(base_url, link)
        
        fingerprint = self.generate_fingerprint(title, None, date.today())
        
        if self.is_duplicate(fingerprint):
            self.skipped += 1
            return
        
        tender = Tender(
            title=title,
            publish_date=date.today(),
            source_url=link,
            summary=self.clean_text(item.get_text()[:200])
        )
        
        db.session.add(tender)
        db.session.flush()
        
        fp = TenderFingerprint(tender_id=tender.id, fingerprint=fingerprint)
        db.session.add(fp)
        
        self.added += 1
    
    def run_task(self, task):
        history = CrawlHistory(
            task_id=task.id,
            status='running',
            start_time=datetime.now()
        )
        db.session.add(history)
        db.session.commit()
        
        try:
            result = self.crawl_website(
                task.website,
                task.keywords,
                task.category,
                task.region
            )
            
            history.status = 'completed'
            history.end_time = datetime.now()
            history.items_found = self.added + self.skipped
            history.items_added = self.added
            history.items_skipped = self.skipped
            history.error_message = '\n'.join(self.errors[:10]) if self.errors else None
            
            task.last_crawl_time = datetime.now()
            task.next_crawl_time = datetime.now()
            task.total_crawled += self.added
            task.success_count += self.added
            task.error_count += len(self.errors)
            
            db.session.commit()
            
        except Exception as e:
            history.status = 'failed'
            history.end_time = datetime.now()
            history.error_message = str(e)
            
            task.status = 'error'
            
            db.session.commit()
