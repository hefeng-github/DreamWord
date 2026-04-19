#!/usr/bin/env python3
"""
从Python版本的SQLite数据库导入词典数据到Cloudflare D1

用法：
python import-dict.py --limit 1000  # 导入前1000个单词
python import-dict.py --all          # 导入所有单词
python import-dict.py --word hello   # 导入特定单词
"""

import sqlite3
import sys
import os
import json
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.word_lookup import WordLookup

class DictionaryImporter:
    """词典导入器"""

    def __init__(self, db_path=None):
        if db_path is None:
            # 默认使用Python版本的数据库
            self.db_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'databases')
            db_path = os.path.join(self.db_dir, 'word_details.db')

        self.db_path = db_path
        self.conn = None

    def connect(self):
        """连接数据库"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        print(f"✅ 已连接数据库: {self.db_path}")

    def get_total_words(self):
        """获取总词数"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT entry) FROM mdx')
        count = cursor.fetchone()[0]
        return count

    def export_words(self, limit=None, specific_word=None):
        """导出单词数据"""

        if specific_word:
            query = 'SELECT entry, paraphrase FROM mdx WHERE entry = ?'
            params = (specific_word,)
        elif limit:
            query = 'SELECT entry, paraphrase FROM mdx GROUP BY entry LIMIT ?'
            params = (limit,)
        else:
            query = 'SELECT entry, paraphrase FROM mdx GROUP BY entry'
            params = ()

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        words = []
        for entry, paraphrase in cursor.fetchall():
            words.append({
                'entry': entry,
                'paraphrase': paraphrase
            })

        return words

    def save_to_json(self, words, output_file):
        """保存为JSON格式（用于导入）"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)

        print(f"✅ 已保存 {len(words)} 个单词到 {output_file}")

    def generate_sql_inserts(self, words, output_file):
        """生成SQL INSERT语句"""

        with open(output_file, 'w', encoding='utf-8') as f:
            for word_data in words:
                entry = word_data['entry'].replace("'", "''")
                paraphrase = word_data['paraphrase'].replace("'", "''")

                sql = f"INSERT OR IGNORE INTO mdx (entry, paraphrase) VALUES ('{entry}', '{paraphrase}');"
                f.write(sql + '\n')

        print(f"✅ 已生成 {len(words)} 条SQL语句到 {output_file}")

    def generate_csv(self, words, output_file):
        """生成CSV格式（适合大批量导入）"""

        import csv

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['entry', 'paraphrase'])

            for word_data in words:
                writer.writerow([
                    word_data['entry'],
                    word_data['paraphrase']
                ])

        print(f"✅ 已生成 {len(words)} 行CSV数据到 {output_file}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

def main():
    parser = argparse.ArgumentParser(description='从SQLite导出词典数据')
    parser.add_argument('--limit', type=int, help='导出的单词数量')
    parser.add_argument('--all', action='store_true', help='导出所有单词')
    parser.add_argument('--word', type=str, help='导出特定单词')
    parser.add_argument('--output', type=str, default='dict-export.json', help='输出文件名')
    parser.add_argument('--format', type=str, default='json', choices=['json', 'sql', 'csv'], help='输出格式')
    parser.add_argument('--db', type=str, help='SQLite数据库路径')

    args = parser.parse_args()

    if not any([args.limit, args.all, args.word]):
        print("❌ 错误: 请指定 --limit, --all 或 --word")
        parser.print_help()
        sys.exit(1)

    try:
        importer = DictionaryImporter(args.db)
        importer.connect()

        # 显示统计信息
        total = importer.get_total_words()
        print(f"📊 数据库总词数: {total}")

        # 导出数据
        if args.limit:
            print(f"📤 导出前 {args.limit} 个单词...")
        elif args.word:
            print(f"📤 导出单词: {args.word}...")
        else:
            print(f"📤 导出所有单词...")

        words = importer.export_words(args.limit, args.word)

        # 根据格式保存
        if args.format == 'json':
            importer.save_to_json(words, args.output)
        elif args.format == 'sql':
            importer.generate_sql_inserts(words, args.output)
        elif args.format == 'csv':
            importer.generate_csv(words, args.output)

        print(f"✅ 导出完成！共 {len(words)} 个单词")

        # 显示下一步操作
        print("\n📝 下一步操作:")
        if args.format == 'sql':
            print(f"1. wrangler d1 execute dreamword-dict --file=./{args.output}")
        elif args.format == 'json':
            print(f"1. 使用脚本导入JSON到D1")
            print(f"2. 或手动转换数据格式")
        elif args.format == 'csv':
            print(f"1. 使用Cloudflare D1批量导入工具")

        importer.close()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
