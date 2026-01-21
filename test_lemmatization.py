import sqlite3
import os
from word_lookup import WordLookup

db_path = os.path.join(os.path.dirname(__file__), 'databases', 'word_details.db')

print("=" * 60)
print("测试数据库和词形还原功能")
print("=" * 60)

# 1. 检查数据库中是否有 'refuse'
print("\n1. 检查数据库中是否有 'refuse':")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT paraphrase FROM mdx WHERE paraphrase LIKE '%>refuse</h1>%' LIMIT 1")
result = cursor.fetchone()
if result:
    print("   ✓ 找到 'refuse' 在数据库中")
else:
    print("   ✗ 未找到 'refuse' 在数据库中")
conn.close()

# 2. 检查数据库中是否有 'refused'
print("\n2. 检查数据库中是否有 'refused':")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT paraphrase FROM mdx WHERE paraphrase LIKE '%>refused</h1>%' LIMIT 1")
result = cursor.fetchone()
if result:
    print("   ✓ 找到 'refused' 在数据库中")
else:
    print("   ✗ 未找到 'refused' 在数据库中")
conn.close()

# 3. 测试词形还原功能
print("\n3. 测试词形还原功能:")
lookup = WordLookup()

# 测试 refused 的词形还原
print("\n   测试 'refused' 的词形还原:")
base_form = lookup.get_word_base_form('refused')
print(f"   返回的基本形式: {base_form}")

# 检查 refused 是否在数据库中
refused_exists = lookup.word_exists('refused')
print(f"   'refused' 在数据库中: {refused_exists}")

# 检查 refuse 是否在数据库中
refuse_exists = lookup.word_exists('refuse')
print(f"   'refuse' 在数据库中: {refuse_exists}")

# 4. 测试简单词形还原规则
print("\n4. 测试简单词形还原规则:")
base_form_simple = lookup.get_word_base_form_simple('refused')
print(f"   简单规则返回的基本形式: {base_form_simple}")

# 5. 测试NLTK词形还原（如果可用）
print("\n5. 测试NLTK词形还原:")
base_form_nltk = lookup.get_word_base_form_nltk('refused')
print(f"   NLTK返回的基本形式: {base_form_nltk}")

print("\n" + "=" * 60)
