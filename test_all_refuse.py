from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("检查 refuse 的所有相关条目")
print("=" * 60)

# 检查 refuse1
print("\n1. 检查 refuse1:")
entries1 = lookup.get_all_entries('refuse1')
print(f'Number of entries: {len(entries1)}')
for i, entry in enumerate(entries1):
    print(f'Entry {i+1}: headword={entry["headword"]}, chinese_defs={entry["chinese_definitions"][:2] if entry["chinese_definitions"] else []}')

# 检查 refuse2
print("\n2. 检查 refuse2:")
entries2 = lookup.get_all_entries('refuse2')
print(f'Number of entries: {len(entries2)}')
for i, entry in enumerate(entries2):
    print(f'Entry {i+1}: headword={entry["headword"]}, chinese_defs={entry["chinese_definitions"][:2] if entry["chinese_definitions"] else []}')

# 检查 refuse
print("\n3. 检查 refuse:")
entries = lookup.get_all_entries('refuse')
print(f'Number of entries: {len(entries)}')
for i, entry in enumerate(entries):
    print(f'Entry {i+1}: headword={entry["headword"]}, chinese_defs={entry["chinese_definitions"][:2] if entry["chinese_definitions"] else []}')
