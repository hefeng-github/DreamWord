from word_lookup import WordLookup
from html.parser import HTMLParser

class DebugParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.entries = []
        self.current_entry = None
        self.current_pos = None
        self.entry_class = None
        self.in_headword = False
        self.in_pos = False
        self.in_def = False
        self.in_chinese = False
        self.just_finished_def = False
        self.current_def_text = None
        self.current_chinese_text = None
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        current_class = attrs_dict.get('class', '')
        
        if tag == 'div' and 'entry' in current_class:
            print(f"Starting entry div, current_class={current_class}")
            # 开始新的条目
            if self.current_entry:
                print(f"  Saving previous entry: {self.current_entry['headword'] if self.current_entry else 'None'}")
                self.entries.append(self.current_entry)
            self.current_entry = {
                'headword': None,
                'pos': None,
                'definitions': [],
                'chinese_definitions': []
            }
            self.entry_class = 'entry'
        
        elif tag == 'h1' and 'headword' in current_class:
            print(f"  Found headword tag")
            self.in_headword = True
        
        elif tag == 'span' and 'pos' in current_class:
            print(f"  Found pos tag")
            self.in_pos = True
        
        elif tag == 'span' and 'def' in current_class:
            print(f"  Found def tag")
            self.in_def = True
            self.current_def_text = ''
        
        elif tag == 'chn' and self.just_finished_def:
            print(f"  Found chn tag")
            self.in_chinese = True
            self.current_chinese_text = ''
    
    def handle_endtag(self, tag):
        if tag == 'div' and self.entry_class == 'entry':
            print(f"Ending entry div, entry_class={self.entry_class}")
            # 结束条目
            if self.current_entry:
                print(f"  Saving entry: {self.current_entry['headword'] if self.current_entry else 'None'}")
                self.entries.append(self.current_entry)
            self.current_entry = None
            self.entry_class = None
        
        elif tag == 'h1' and self.in_headword:
            print(f"  Ending headword tag")
            self.in_headword = False
        
        elif tag == 'span' and self.in_pos:
            print(f"  Ending pos tag, pos={self.current_pos if hasattr(self, 'current_pos') else 'None'}")
            self.in_pos = False
        
        elif tag == 'span' and self.in_def:
            print(f"  Ending def tag, def_text={self.current_def_text[:50] if self.current_def_text else 'None'}")
            if self.current_def_text:
                self.current_entry['definitions'].append(self.current_def_text.strip())
                self.just_finished_def = True
            self.in_def = False
            self.current_def_text = None
        
        elif tag == 'chn' and self.in_chinese:
            print(f"  Ending chn tag, chn_text={self.current_chinese_text[:50] if self.current_chinese_text else 'None'}")
            if self.current_chinese_text:
                self.current_entry['chinese_definitions'].append(self.current_chinese_text.strip())
                self.just_finished_def = False
            self.in_chinese = False
            self.current_chinese_text = None
    
    def handle_data(self, data):
        if self.in_headword and not self.current_entry['headword']:
            self.current_entry['headword'] = data.strip()
            print(f"    Setting headword: {data.strip()}")
        elif self.in_pos and not self.current_entry['pos']:
            self.current_pos = data.strip()
            print(f"    Setting pos: {data.strip()}")
        elif self.in_def and self.current_def_text is not None:
            self.current_def_text += data
            print(f"    Adding to def: {data[:30]}")
        elif self.in_chinese and self.current_chinese_text is not None:
            self.current_chinese_text += data
            print(f"    Adding to chn: {data[:30]}")

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
    print(f'definitions: {entry.get("definitions", [])}')
    print(f'chinese_definitions: {entry.get("chinese_definitions", [])}')

conn.close()
