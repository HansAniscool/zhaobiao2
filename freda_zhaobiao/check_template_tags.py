#!/usr/bin/env python3

with open('app/templates/search.html', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print('精确统计模板标签:')
print('=' * 60)

if_count = 0
elif_count = 0
else_count = 0
endif_count = 0

for i, line in enumerate(lines, 1):
    # 排除单行条件 (if 和 endif 在同一行)
    if '{% if' in line and '{% endif %}' not in line:
        if_count += 1
        print(f'行 {i}: if ({line.strip()[:60]})')
    elif '{% elif' in line:
        elif_count += 1
        print(f'行 {i}: elif ({line.strip()[:60]})')
    elif '{% else %}' in line and '{% endif %}' not in line:
        else_count += 1
        print(f'行 {i}: else ({line.strip()[:60]})')
    elif '{% endif %}' in line:
        # 检查是否是单行条件的一部分
        if '{% if' not in line:
            endif_count += 1
            print(f'行 {i}: endif ({line.strip()[:60]})')

print('=' * 60)
print(f'统计结果:')
print(f'  if 语句: {if_count}')
print(f'  elif 语句: {elif_count}')
print(f'  else 语句: {else_count}')
print(f'  endif 语句: {endif_count}')
print(f'  条件总数 (if + elif + else): {if_count + elif_count + else_count}')
print(f'  结束标签 (endif): {endif_count}')

if if_count + elif_count + else_count == endif_count:
    print('✅ 条件标签配对正确')
else:
    print('❌ 条件标签不匹配')
    diff = (if_count + elif_count + else_count) - endif_count
    print(f'   差异: {diff}')
