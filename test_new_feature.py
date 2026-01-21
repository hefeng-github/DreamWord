from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("测试修复后的功能")
print("=" * 60)

# 测试1: 原来的 lookup 方法
print("\n1. 测试原来的 lookup 方法 (refused):")
result = lookup.lookup('refused', 'He refused to help me')
if result['success']:
    print(f"单词: {result['word']}")
    if result['base_form']:
        print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义:")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

# 测试2: 新的 lookup_base_form_only 方法
print("\n2. 测试新的 lookup_base_form_only 方法 (refused):")
result = lookup.lookup_base_form_only('refused')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (前两个):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

# 测试3: 直接查询原型
print("\n3. 测试 lookup_base_form_only 方法 (refuse):")
result = lookup.lookup_base_form_only('refuse')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (前两个):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

# 测试4: 测试另一个词
print("\n4. 测试 lookup_base_form_only 方法 (running):")
result = lookup.lookup_base_form_only('running')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (前两个):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

print("\n" + "=" * 60)
