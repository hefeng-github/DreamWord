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

# 查找HTML中是否有两个entry div
entry_pattern = r'<div class="entry"[^>]*>'
entry_matches = list(re.finditer(entry_pattern, html))

print(f'Found {len(entry_matches)} entry divs')

# 查找第一个entry div的位置
if entry_matches:
    first_pos = entry_matches[0].start()
    print(f'\nFirst entry div starts at position: {first_pos}')
    
    # 查找第一个entry div的结束位置
    # 需要找到对应的 </div>
    div_count = 0
    for i in range(first_pos, min(first_pos + 10000, len(html))):
        if html[i:i+4] == '<div':
            div_count += 1
        elif html[i:i+6] == '</div>':
            div_count -= 1
            if div_count == 0:
                print(f'First entry div ends at position: {i+6}')
                first_entry_end = i + 6
                break
    
    # 查找第二个entry div
    second_match = entry_matches[1] if len(entry_matches) > 1 else None
    if second_match:
        second_pos = second_match.start()
        print(f'\nSecond entry div starts at position: {second_pos}')
        
        # 提取两个entry之间的内容
        if first_entry_end:
            between = html[first_entry_end:second_pos]
            print(f'\nContent between entries ({len(between)} chars):')
            print(between[:500])
            print('...')

conn.close()
