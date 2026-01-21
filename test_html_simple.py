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
print("查找HTML结构")
print("=" * 60)

# 查找第一个entry div
first_entry_start = html.find('<div class="entry"')
print(f'First entry div starts at: {first_entry_start}')

# 查找第一个entry div的结束
# 简单的方法：找到第一个 </div> 在 entry div 之后
after_first_entry = html[first_entry_start:]
first_div_end = after_first_entry.find('</div>')
print(f'First entry div ends at: {first_entry_start + first_div_end + 6}')

# 查找第二个entry div
second_entry_start = html.find('<div class="entry"', first_entry_start + first_div_end + 6)
print(f'\nSecond entry div starts at: {second_entry_start}')

if second_entry_start > 0:
    # 提取两个entry之间的内容
    between = html[first_entry_start + first_div_end + 6:second_entry_start]
    print(f'\nContent between entries ({len(between)} chars):')
    print(between[:500])
    print('...')
    
    # 查找第二个entry中的内容
    second_entry_content = html[second_entry_start:second_entry_start+500]
    print(f'\nSecond entry content (first 500 chars):')
    print(second_entry_content)

conn.close()
