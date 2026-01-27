"""
JSON文件验证和修复工具

用于验证和修复从kajweb/dict下载的单词JSON文件
"""

import json
import sys
import os
from pathlib import Path


def validate_json_file(file_path):
    """
    验证JSON文件格式

    Args:
        file_path: JSON文件路径

    Returns:
        (is_valid, error_message, data)
    """
    print(f"正在验证文件: {file_path}")
    print("=" * 70)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return False, "文件不存在", None

    # 检查文件大小
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size:,} 字节 ({file_size / 1024 / 1024:.2f} MB)")

    if file_size == 0:
        return False, "文件为空", None

    # 尝试读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print("✓ 文件读取成功")
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            print("⚠ 使用GBK编码读取文件")
        except Exception as e:
            return False, f"文件编码错误: {e}", None
    except Exception as e:
        return False, f"读取文件失败: {e}", None

    # 检查BOM
    if content.startswith('\ufeff'):
        content = content[1:]
        print("⚠ 检测到BOM，已移除")

    # 去除首尾空白
    content = content.strip()

    # 检查是否为空
    if not content:
        return False, "文件内容为空", None

    # 尝试解析JSON
    try:
        data = json.loads(content)
        print("✓ JSON格式验证通过")

        # 检查数据类型
        if isinstance(data, list):
            print(f"✓ 数据类型: 数组，包含 {len(data)} 个单词")
            if len(data) > 0:
                print(f"  第一个单词: {data[0].get('headWord', 'unknown')}")
        elif isinstance(data, dict):
            print("✓ 数据类型: 单个对象")
            print(f"  单词: {data.get('headWord', 'unknown')}")
        else:
            print(f"⚠ 未知数据类型: {type(data)}")

        return True, None, data

    except json.JSONDecodeError as e:
        print(f"✗ 标准JSON解析失败: {e.msg}")
        print("  尝试解析为 JSON Lines 格式...")

        # 尝试JSON Lines格式（每行一个JSON对象）
        try:
            lines = content.split('\n')
            words_data = []
            parse_count = 0
            error_count = 0

            for i, line in enumerate(lines):
                line = line.strip()

                # 跳过空行和注释
                if not line or line.startswith('//') or line.startswith('#'):
                    continue

                try:
                    obj = json.loads(line)
                    if 'headWord' in obj:
                        words_data.append(obj)
                        parse_count += 1
                except json.JSONDecodeError:
                    error_count += 1
                    if error_count <= 3:
                        print(f"  第 {i+1} 行解析失败")

            if len(words_data) > 0:
                print(f"✓ JSON Lines格式验证通过")
                print(f"✓ 数据类型: JSON Lines，包含 {len(words_data)} 个单词")
                if len(words_data) > 0:
                    print(f"  第一个单词: {words_data[0].get('headWord', 'unknown')}")
                return True, None, words_data
            else:
                return False, "未找到有效的JSON对象", None

        except Exception as e2:
            error_msg = f"JSON格式错误，也不是有效的JSON Lines格式"
            print(f"✗ {error_msg}")

            # 显示原始错误位置
            line_num = e.lineno
            col_num = e.colno
            if line_num:
                print(f"  错误位置: 第 {line_num} 行，第 {col_num} 列")

            return False, error_msg, None
    except Exception as e:
        return False, f"解析JSON时发生未知错误: {e}", None


def fix_json_file(input_path, output_path=None):
    """
    尝试修复JSON文件

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）

    Returns:
        (success, message)
    """
    print("\n" + "=" * 70)
    print("尝试修复JSON文件...")
    print("=" * 70)

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_fixed{ext}"

    try:
        # 读取文件
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_size = len(content)

        # 移除BOM
        if content.startswith('\ufeff'):
            content = content[1:]
            print("✓ 移除BOM")

        # 去除首尾空白和注释（某些JSON文件可能有注释）
        lines = content.split('\n')
        cleaned_lines = []

        in_string = False
        for line in lines:
            # 跳过注释行
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('#'):
                continue

            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # 尝试解析
        try:
            data = json.loads(content)
            print("✓ JSON格式正确，无需修复")
            return True, "文件格式正确，无需修复"
        except json.JSONDecodeError as e:
            # 尝试修复常见问题
            print(f"⚠ JSON格式错误: {e.msg}")

            # 修复1: 移除尾部逗号
            print("\n尝试修复1: 移除尾部逗号...")
            content_fixed = content.replace(r',\s*}', '}', 100000)  # 全局替换
            content_fixed = content_fixed.replace(r',\s*]', ']', 100000)

            try:
                data = json.loads(content_fixed)
                print("✓ 修复成功：移除了尾部逗号")

                # 保存修复后的文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content_fixed)

                file_size = len(content_fixed)
                print(f"✓ 修复后的文件已保存到: {output_path}")
                print(f"  原始大小: {original_size:,} 字节")
                print(f"  修复后大小: {file_size:,} 字节")

                return True, f"已修复并保存到 {output_path}"
            except:
                pass

            # 修复2: 移除注释（如果存在）
            print("\n尝试修复2: 移除注释...")
            lines = content.split('\n')
            cleaned_lines = []

            for line in lines:
                # 跳过整行注释
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('#'):
                    continue

                # 移除行内注释
                if '//' in line and '"' not in line.split('//')[0]:
                    line = line.split('//')[0]

                cleaned_lines.append(line)

            content_fixed = '\n'.join(cleaned_lines)

            try:
                data = json.loads(content_fixed)
                print("✓ 修复成功：移除了注释")

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content_fixed)

                print(f"✓ 修复后的文件已保存到: {output_path}")
                return True, f"已修复并保存到 {output_path}"
            except:
                pass

            return False, "无法自动修复此JSON文件"

    except Exception as e:
        return False, f"修复失败: {e}"


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python validate_json.py <json文件路径>")
        print("\n示例:")
        print("  python validate_json.py GaoZhong_3.json")
        print("  python validate_json.py GaoZhong_3.json --fix")
        return

    file_path = sys.argv[1]

    # 验证文件
    is_valid, error_msg, data = validate_json_file(file_path)

    if is_valid:
        print("\n" + "=" * 70)
        print("✓ 验证通过！文件格式正确")
        print("=" * 70)

        # 显示统计信息
        if isinstance(data, list) and len(data) > 0:
            print(f"\n单词统计:")
            print(f"  总数: {len(data)}")

            # 显示前5个单词
            print(f"\n前5个单词:")
            for i, item in enumerate(data[:5]):
                word = item.get('headWord', 'unknown')
                content = item.get('content', {})
                word_content = content.get('word', {})
                word_inner = word_content.get('content', {})

                phonetic = word_inner.get('usphone') or word_inner.get('ukphone') or 'N/A'
                trans = word_inner.get('trans', [])
                definition = trans[0].get('tranCn', 'N/A') if trans else 'N/A'

                print(f"  {i+1}. {word} [{phonetic}] - {definition}")

            if len(data) > 5:
                print(f"  ... 还有 {len(data) - 5} 个单词")

        return 0

    else:
        print("\n" + "=" * 70)
        print(f"✗ 验证失败: {error_msg}")
        print("=" * 70)

        # 询问是否修复
        if '--fix' in sys.argv:
            success, msg = fix_json_file(file_path)
            if success:
                print(f"\n✓ {msg}")
                return 0
            else:
                print(f"\n✗ {msg}")
                return 1
        else:
            print("\n提示:")
            print("  如果想尝试自动修复，请运行:")
            print(f"  python validate_json.py {file_path} --fix")
            return 1


if __name__ == '__main__':
    sys.exit(main())
