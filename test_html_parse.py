from word_lookup import WordLookup
import sqlite3
import re

lookup = WordLookup()
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print('=== 查找中文释义 ===')
chn_tags = re.findall(r'<chn>.*?</chn>', html, re.DOTALL)
print(f'Found {len(chn_tags)} <chn> tags')
print('First 5 <chn> tags:')
for i, tag in enumerate(chn_tags[:5]):
    print(f'{i+1}. {tag[:150]}...')

print('\n=== 查找英文释义 ===')
def_tags = re.findall(r'<span class="def"[^>]*>.*?</span>', html, re.DOTALL)
print(f'Found {len(def_tags)} <span class="def"> tags')
print('First 3 definitions:')
for i, tag in enumerate(def_tags[:3]):
    print(f'{i+1}. {tag[:200]}...')

print('\n=== 查找例句 ===')
x_tags = re.findall(r'<span class="x"[^>]*>.*?</span>', html, re.DOTALL)
print(f'Found {len(x_tags)} <span class="x"> tags')
print('First 3 examples:')
for i, tag in enumerate(x_tags[:3]):
    print(f'{i+1}. {tag[:200]}...')

print('\n=== 查找音标 ===')
phon_tags = re.findall(r'<span class="phon"[^>]*>.*?</span>', html, re.DOTALL)
print(f'Found {len(phon_tags)} <span class="phon"> tags')
print('All phonetics:')
for i, tag in enumerate(phon_tags):
    print(f'{i+1}. {tag}')

print('\n=== 查找headword ===')
hw_tags = re.findall(r'<h1 class="headword"[^>]*>.*?</h1>', html, re.DOTALL)
print(f'Found {len(hw_tags)} <h1 class="headword"> tags')
print('All headwords:')
for i, tag in enumerate(hw_tags):
    print(f'{i+1}. {tag}')

conn.close()
