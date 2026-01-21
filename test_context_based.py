from word_lookup import WordLookup

lookup = WordLookup()

print("=" * 60)
print("测试根据语境判断最合适释义的 lookup_base_form_only 方法")
print("=" * 60)

# 测试1: refused - 拒绝的语境
print("\n1. 测试 lookup_base_form_only (refused) - 拒绝的语境:")
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

# 测试2: refused - 垃圾的语境
print("\n2. 测试 lookup_base_form_only (refused) - 垃圾的语境:")
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

# 测试3: 没有语境
print("\n3. 测试 lookup_base_form_only (refuse) - 无语境:")
result = lookup.lookup_base_form_only('refuse')
if result['success']:
    print(f"单词: {result['word']}")
    print(f"原形: {result['base_form']}")
    print(f"音标: {result['phonetic']}")
    print(f"\n中文释义 (默认第一个):")
    for i, definition in enumerate(result['definitions'], 1):
        print(f"  {i}. {definition}")
else:
    print(f"错误: {result['message']}")

print("\n" + "=" * 60)
