from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print('=== 查找所有 entry div ===')
entry_divs = re.findall(r'<div class="entry"[^>]*>.*?</div>', html, re.DOTALL)
print(f'Found {len(entry_divs)} entry divs')

for i, div in enumerate(entry_divs):
    print(f'\n--- Entry {i+1} ---')
    # 提取headword
    hw_match = re.search(r'<h1 class="headword"[^>]*>([^<]+)</h1>', div)
    if hw_match:
        print(f'headword: {hw_match.group(1)}')
    
    # 提取pos
    pos_match = re.search(r'<span class="pos"[^>]*>([^<]+)</span>', div)
    if pos_match:
        print(f'pos: {pos_match.group(1)}')
    
    # 提取中文释义
    chn_matches = re.findall(r'<chn>([^<]+)</chn>', div)
    print(f'chinese definitions: {chn_matches[:2]}')

conn.close()
