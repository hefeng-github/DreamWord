from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("测试HTML解析器")
print("=" * 60)

# 测试 parse_entry
print("\n1. 测试 parse_entry:")
entries = lookup.parse_entry(lookup._execute_query('SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1', ('refuse',), fetch_one=True)[0])
print(f'Type: {type(entries)}')
print(f'Number of entries: {len(entries) if isinstance(entries, list) else 1}')

if isinstance(entries, list):
    for i, entry in enumerate(entries):
        print(f'\n--- Entry {i+1} ---')
        print(f'headword: {entry.get("headword", "N/A")}')
        print(f'pos: {entry.get("pos", "N/A")}')
        print(f'phonetics: {entry.get("phonetics", [])}')
        print(f'definitions: {entry.get("definitions", [])}')
        print(f'chinese_definitions: {entry.get("chinese_definitions", [])}')
else:
    print(f'\n--- Single Entry ---')
    print(f'headword: {entries.get("headword", "N/A")}')
    print(f'pos: {entries.get("pos", "N/A")}')
    print(f'phonetics: {entries.get("phonetics", [])}')
    print(f'definitions: {entries.get("definitions", [])}')
    print(f'chinese_definitions: {entries.get("chinese_definitions", [])}')

print("\n" + "=" * 60)
