#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试查词预览功能
"""

import sys
import os

# 添加项目路径到sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

def test_word_lookup():
    """测试查词功能"""
    print("=" * 50)
    print("Testing Word Preview Function")
    print("=" * 50)

    try:
        from src.modules.word_lookup import WordLookup

        # 创建查词实例
        print("\n1. Initializing word lookup module...")
        word_lookup = WordLookup()
        print("   [OK] Word lookup module initialized successfully")

        # 测试查词
        test_words = ["hello", "world", "computer", "python", "test"]

        for word in test_words:
            print(f"\n2. Looking up word: {word}")
            result = word_lookup.lookup(word)

            if result.success:
                print(f"   [OK] Word: {result.word}")
                print(f"   [OK] Phonetic: {result.phonetic}")
                print(f"   [OK] POS: {result.pos}")
                print(f"   [OK] Definitions: {', '.join(result.definitions[:2])}")  # 只显示前两个释义
                if result.base_form and result.base_form != result.word:
                    print(f"   [OK] Base form: {result.base_form}")
                if result.examples:
                    print(f"   [OK] Examples count: {len(result.examples)}")
            else:
                print(f"   [FAIL] Lookup failed: {result.message}")

        print("\n" + "=" * 50)
        print("[OK] Word preview function test completed!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """测试API端点"""
    print("\n" + "=" * 50)
    print("Testing Flask API Endpoint")
    print("=" * 50)

    try:
        from app import app

        print("\n1. Creating test client...")
        with app.test_client() as client:
            print("   [OK] Test client created successfully")

            # 测试查词API
            test_word = "hello"
            print(f"\n2. Testing API endpoint: /api/word-preview?word={test_word}")

            response = client.get(f'/api/word-preview?word={test_word}')
            print(f"   [OK] Status code: {response.status_code}")

            if response.status_code == 200:
                data = response.get_json()
                print(f"   [OK] Response type: application/json")

                if data.get('success'):
                    print(f"   [OK] Word: {data.get('word')}")
                    print(f"   [OK] Phonetic: {data.get('phonetic')}")
                    print(f"   [OK] POS: {data.get('pos')}")
                    print(f"   [OK] Definitions count: {len(data.get('definitions', []))}")
                else:
                    print(f"   [FAIL] API returned error: {data.get('error')}")
            else:
                print(f"   [FAIL] HTTP error: {response.status_code}")

        print("\n" + "=" * 50)
        print("[OK] API endpoint test completed!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # 设置UTF-8输出编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # 测试查词功能
    lookup_ok = test_word_lookup()

    # 测试API端点
    api_ok = test_api_endpoint()

    # 总结
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Word Lookup: {'[PASS]' if lookup_ok else '[FAIL]'}")
    print(f"API Endpoint: {'[PASS]' if api_ok else '[FAIL]'}")

    if lookup_ok and api_ok:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some tests failed")
        sys.exit(1)
