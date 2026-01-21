from word_lookup import WordLookup
from html.parser import HTMLParser

class DebugParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.entries = []
        self.current_entry = None
        self.current_pos = None
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        current_class = attrs_dict.get('class', '')
        
        if tag == 'div' and 'entry' in current_class:
            # 开始新的条目
            if self.current_entry:
                self.entries.append(self.current_entry)
            self.current_entry = {
                'headword': None,
                'pos': None,
                'definitions': [],
                'chinese_definitions': []
            }
            print(f"Starting new entry div")
        
        elif tag == 'h1' and 'headword' in current_class:
            print(f"Found headword tag")
        
        elif tag == 'span' and 'pos' in current_class:
            print(f"Found pos tag")
    
    def handle_endtag(self, tag):
        if tag == 'div' and 'entry' in self.current_class:
            # 结束条目
            if self.current_entry:
                self.entries.append(self.current_entry)
                print(f"Ending entry div, total entries: {len(self.entries)}")
            self.current_entry = None

lookup = WordLookup()
import sqlite3
conn = sqlite3.connect(lookup.word_details_path)
cursor = conn.cursor()

cursor.execute('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',))
result = cursor.fetchone()
html = result[0]

print("=" * 60)
print("调试HTML解析器")
print("=" * 60)

parser = DebugParser()
parser.feed(html)

print(f"\nTotal entries found: {len(parser.entries)}")
for i, entry in enumerate(parser.entries):
    print(f'\n--- Entry {i+1} ---')
    print(f'headword: {entry.get("headword", "N/A")}')
    print(f'pos: {entry.get("pos", "N/A")}')

conn.close()
