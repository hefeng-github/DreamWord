from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("测试修改后的 lookup_base_form_only 方法")
print("=" * 60)

# 测试1: refused
print("\n1. 测试 lookup_base_form_only (refused):")
result = lookup.lookup_base_form_only('refused')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (全部):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

# 测试2: refuse
print("\n2. 测试 lookup_base_form_only (refuse):")
result = lookup.lookup_base_form_only('refuse')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (全部):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

print("\n" + "=" * 60)
