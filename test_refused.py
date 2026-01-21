from word_lookup import WordLookup

lookup = WordLookup()
entries = lookup.get_all_entries('refused')
print('Number of entries:', len(entries))
for i, e in enumerate(entries):
    print(f'Entry {i+1}: headword={e["headword"]}, chinese_defs={len(e["chinese_definitions"])}, examples={len(e["examples"])}')
    print(f'  Chinese definitions: {e["chinese_definitions"][:3]}')
    print(f'  Examples: {e["examples"][:2]}')
