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
print("查找entry div的位置")
print("=" * 60)

# 查找所有 entry div
entry_divs = re.finditer(r'<div class="entry"[^>]*>', html)
print(f'Found {len(list(entry_divs))} entry divs')

positions = []
for match in entry_divs:
    positions.append(match.start())

print(f'\nEntry div positions: {positions}')

# 查找第一个和第二个entry div之间的内容
if len(positions) >= 2:
    between_divs = html[positions[0]:positions[1]]
    print(f'\nContent between first and second entry div ({len(between_divs)} chars):')
    print(between_divs[:500])
    print('...')

# 查找所有 </div> 标签
close_divs = [m.start() for m in re.finditer(r'</div>', html)]
print(f'\n\nFound {len(close_divs)} </div> tags')
print(f'First 10 positions: {close_divs[:10]}')

conn.close()
