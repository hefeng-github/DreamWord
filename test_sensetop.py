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
print("检查sensetop标签")
print("=" * 60)

# 查找所有 sensetop 标签
sensetop_matches = re.findall(r'<span class="sensetop"[^>]*>.*?</span>', html, re.DOTALL)
print(f'Found {len(sensetop_matches)} sensetop tags')

for i, match in enumerate(sensetop_matches):
    print(f'\n--- Sensetop {i+1} ---')
    print(f'{match[:300]}...')

# 查找 sensetop 之后的 def
for i, match in enumerate(sensetop_matches):
    after_sensetop = html[html.find(match) + len(match):]
    # 查找接下来的500个字符中的def
    defs_after = re.findall(r'<span class="def"[^>]*>.*?</span>', after_sensetop[:500], re.DOTALL)
    print(f'\nDefs after sensetop {i+1}: {len(defs_after)}')

conn.close()
