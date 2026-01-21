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
print("检查第一个entry div的完整内容")
print("=" * 60)

# 查找第一个entry div
first_entry_start = html.find('<div class="entry"')
first_entry_end = html.find('</div>', first_entry_start)
first_entry = html[first_entry_start:first_entry_end + 6]

print(f'First entry div ({len(first_entry)} chars):')
print(first_entry)

conn.close()
