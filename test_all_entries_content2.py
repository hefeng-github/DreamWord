from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print("=" * 60)
print("检查所有entry div的内容")
print("=" * 60)

# 查找所有 entry div，使用非贪婪匹配
entry_pattern = r'<div class="entry"[^>]*>.*?</div>'
entry_divs = re.findall(entry_pattern, html, re.DOTALL)

print(f'Found {len(entry_divs)} entry divs')

for i, div in enumerate(entry_divs):
    print(f'\n--- Entry {i+1} ({len(div)} chars) ---')
    
    # 查找def标签
    def_tags = re.findall(r'<span class="def"[^>]*>.*?</span>', div, re.DOTALL)
    print(f'Number of def tags: {len(def_tags)}')
    
    # 查找chn标签
    chn_tags = re.findall(r'<chn>([^<]+)</chn>', div)
    print(f'Number of chn tags: {len(chn_tags)}')
    
    if def_tags:
        print(f'First def tag: {def_tags[0][:200]}...')
    if chn_tags:
        print(f'First chn tag: {chn_tags[0]}')

conn.close()
