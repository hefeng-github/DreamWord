from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("检查 refuse 的所有条目结构")
print("=" * 60)

entries = lookup.get_all_entries('refuse')
print(f'Number of entries: {len(entries)}')

for i, entry in enumerate(entries):
    print(f'\n--- Entry {i+1} ---')
    print(f'headword: {entry["headword"]}')
    print(f'phonetics: {entry["phonetics"]}')
    print(f'definitions (English): {entry["definitions"][:2] if entry["definitions"] else []}')
    print(f'chinese_definitions: {entry["chinese_definitions"][:3] if entry["chinese_definitions"] else []}')
    print(f'base_form: {entry["base_form"]}')
