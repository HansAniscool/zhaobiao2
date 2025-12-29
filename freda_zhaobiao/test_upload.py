#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

session = requests.Session()

# 1. 先访问页面获取 CSRF token
response = session.get('http://localhost:5001/admin/websites/upload')
print(f'页面状态: {response.status_code}')

# 2. 从响应中提取 CSRF token
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
print(f'CSRF Token获取成功')

# 3. 上传文件
files = {'file': ('test_websites_correct.xlsx', open('test_websites_correct.xlsx', 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
data = {'csrf_token': csrf_token}
response = session.post('http://localhost:5001/admin/websites/upload', files=files, data=data)

print(f'上传状态: {response.status_code}')
print(f'重定向到: {response.url}')

# 4. 获取结果页面
result_response = session.get(response.url)
result_soup = BeautifulSoup(result_response.text, 'html.parser')

# 5. 检查页面中的消息
for elem in result_soup.find_all(['div', 'p', 'span']):
    text = elem.get_text()
    if any(keyword in text for keyword in ['成功', '导入', '添加', '更新', '个网站', '条']):
        print(f'结果消息: {text.strip()[:80]}')
