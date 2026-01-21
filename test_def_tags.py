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
print("检查definition标签结构")
print("=" * 60)

# 查找所有包含 def 的标签
def_patterns = [
    r'<span class="def"[^>]*>.*?</span>',
    r'<span class="def"[^>]*>([^<]+)</span>',
    r'<span[^>]*class="def"[^>]*>.*?</span>',
]

for i, pattern in enumerate(def_patterns):
    matches = re.findall(pattern, html, re.DOTALL)
    print(f'\nPattern {i+1}: {pattern}')
    print(f'Found {len(matches)} matches')
    if matches:
        print(f'First match: {matches[0][:200]}...')

# 查找所有 span 标签
span_tags = re.findall(r'<span[^>]*>.*?</span>', html, re.DOTALL)
print(f'\n\nTotal span tags found: {len(span_tags)}')

# 查找包含 class="def" 的 span
def_spans = [span for span in span_tags if 'class="def"' in span or "class='def'" in span]
print(f'Span tags with class="def": {len(def_spans)}')

if def_spans:
    print(f'\nFirst 5 def spans:')
    for i, span in enumerate(def_spans[:5]):
        print(f'{i+1}. {span[:200]}...')

conn.close()
