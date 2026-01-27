"""
快速测试JSON文件格式
"""
import sys
import json

file_path = sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\Lenovo\OneDrive1\桌面\GaoZhong_3.json"

print(f"Testing file: {file_path}")
print("=" * 50)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"File size: {len(content):,} bytes")
    print(f"First 200 characters:\n{content[:200]}")
    print("\n" + "=" * 50)

    # Try to parse as JSON Lines
    lines = content.split('\n')
    words = []

    for i, line in enumerate(lines[:10]):  # Test first 10 lines
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
            if 'headWord' in obj:
                words.append(obj['headWord'])
                print(f"[OK] Line {i+1}: {obj['headWord']}")
        except Exception as e:
            print(f"[FAIL] Line {i+1}: {str(e)[:50]}")

    print("\n" + "=" * 50)
    print(f"Result: Found {len(words)} words in first 10 lines")
    print("Format: JSON Lines (one JSON object per line)")

except Exception as e:
    print(f"Error: {e}")
