import re

with open('search.html', 'r') as f:
    content = f.read()

if_count = len(re.findall(r'\{%', content))
endif_count = len(re.findall(r'%\}', content))

print(f'Template tag count: {if_count}')
print(f'Template end tag count: {endif_count}')

if_lines = []
for i, line in enumerate(content.split('\n'), 1):
    if '{%' in line and '{%-' not in line:
        if_lines.append(f'{i}: {line.strip()}')

print('\nAll template tags:')
for line in if_lines:
    print(line)

print('\n=== Checking for unmatched tags ===')

# Simple check - count opening and closing blocks
if_blocks = content.count('{% if') + content.count('{% elif')
endif_blocks = content.count('{% endif %}')

print(f'If/elif blocks: {if_blocks}')
print(f'Endif blocks: {endif_blocks}')
