from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print('=== 查找所有词性 ===')
pos_tags = re.findall(r'<span class="pos"[^>]*>([^<]+)</span>', html)
print(f'Found {len(pos_tags)} parts of speech:')
for i, pos in enumerate(pos_tags):
    print(f'{i+1}. {pos}')

print('\n=== 查找所有headword ===')
hw_tags = re.findall(r'<h1 class="headword"[^>]*>.*?</h1>', html, re.DOTALL)
print(f'Found {len(hw_tags)} headwords:')
for i, hw in enumerate(hw_tags):
    print(f'{i+1}. {hw[:200]}...')

print('\n=== 查找所有中文释义 ===')
chn_tags = re.findall(r'<chn>([^<]+)</chn>', html)
print(f'Found {len(chn_tags)} Chinese definitions:')
for i, chn in enumerate(chn_tags):
    print(f'{i+1}. {chn}')

conn.close()
