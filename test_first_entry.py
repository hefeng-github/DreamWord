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
print("检查第一个entry div的内容")
print("=" * 60)

# 查找第一个entry div
first_entry_start = html.find('<div class="entry"')
first_entry_end = html.find('</div>', first_entry_start)
first_entry = html[first_entry_start:first_entry_end + 6]

print(f'First entry div length: {len(first_entry)}')

# 查找第一个entry中的def标签
def_tags = re.findall(r'<span class="def"[^>]*>.*?</span>', first_entry, re.DOTALL)
print(f'Number of def tags in first entry: {len(def_tags)}')

if def_tags:
    print(f'First 3 def tags:')
    for i, tag in enumerate(def_tags[:3]):
        print(f'{i+1}. {tag[:200]}...')

# 查找第一个entry中的chn标签
chn_tags = re.findall(r'<chn>([^<]+)</chn>', first_entry)
print(f'\nNumber of chn tags in first entry: {len(chn_tags)}')

if chn_tags:
    print(f'First 3 chn tags:')
    for i, tag in enumerate(chn_tags[:3]):
        print(f'{i+1}. {tag}')

conn.close()
