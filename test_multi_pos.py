from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("测试修改后的多词性解析")
print("=" * 60)

# 测试1: 获取 refuse 的所有条目
print("\n1. 获取 refuse 的所有条目:")
entries = lookup.get_all_entries('refuse')
print(f'Number of entries: {len(entries)}')
for i, entry in enumerate(entries):
    print(f'\n--- Entry {i+1} ---')
    print(f'headword: {entry["headword"]}')
    print(f'pos: {entry.get("pos", "N/A")}')
    print(f'phonetics: {entry["phonetics"][:2]}')
    print(f'definitions (English): {entry["definitions"][:2] if entry["definitions"] else []}')
    print(f'chinese_definitions: {entry["chinese_definitions"][:3] if entry["chinese_definitions"] else []}')

# 测试2: lookup_base_form_only with context
print("\n2. 测试 lookup_base_form_only (refused) - 拒绝的语境:")
result = lookup.lookup_base_form_only('refused', 'He refused to help me')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (最合适的):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

# 测试3: lookup_base_form_only with trash context
print("\n3. 测试 lookup_base_form_only (refused) - 垃圾的语境:")
result = lookup.lookup_base_form_only('refused', 'The trash was refused')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (最合适的):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

print("\n" + "=" * 60)
