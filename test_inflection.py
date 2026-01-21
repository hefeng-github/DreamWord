from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print('=== 查找所有可能的词形还原标记 ===')

# 查找所有可能的标记
patterns = [
    r'<span class="xrefs"[^>]*>.*?</span>',
    r'<span class="xh"[^>]*>.*?</span>',
    r'<span class="infl"[^>]*>.*?</span>',
    r'<span class="irreg"[^>]*>.*?</span>',
    r'<span class="gram"[^>]*>.*?</span>',
]

for pattern in patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f'\nPattern: {pattern}')
        for i, match in enumerate(matches[:2]):
            print(f'{i+1}. {match[:200]}...')

# 查找 headword 附近的内容
hw_match = re.search(r'<h1 class="headword"[^>]*>.*?</h1>', html, re.DOTALL)
if hw_match:
    print(f'\n=== Headword附近的内容 ===')
    print(hw_match.group(0)[:500])

conn.close()
