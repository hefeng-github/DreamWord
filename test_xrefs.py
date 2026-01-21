from word_lookup import WordLookup
import re

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

xrefs = re.findall(r'<span class="xrefs"[^>]*>.*?</span>', html, re.DOTALL)
print('Found xrefs:')
for i, xref in enumerate(xrefs[:3]):
    print(f'{i+1}. {xref[:300]}...')

xhs = re.findall(r'<span class="xh"[^>]*>([^<]+)</span>', html)
print('\nFound xh tags:')
for i, xh in enumerate(xhs):
    print(f'{i+1}. {xh}')

conn.close()
