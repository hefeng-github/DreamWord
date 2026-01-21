from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

# 找到第一个 entry div
entry_divs = re.findall(r'<div class="entry"[^>]*>.*?</div>', html, re.DOTALL)

if entry_divs:
    first_entry = entry_divs[0]
    print('=== 第一个 entry div 的结构 ===')
    
    # 查找所有标签
    all_tags = re.findall(r'<([a-z]+)[^>]*>', first_entry, re.IGNORECASE)
    print(f'Found {len(all_tags)} tags')
    
    # 查找 pos 标签的位置
    pos_tags = re.finditer(r'<span class="pos"[^>]*>.*?</span>', first_entry, re.DOTALL)
    print(f'\nFound {len(list(pos_tags))} pos tags:')
    for i, match in enumerate(pos_tags):
        start = match.start()
        end = match.end()
        context_before = first_entry[max(0, start-100):start]
        context_after = first_entry[end:min(len(first_entry), end+100)]
        print(f'\nPos {i+1}:')
        print(f'  Before: ...{context_before}')
        print(f'  Tag: {match.group(0)}')
        print(f'  After: {context_after}...')

conn.close()
