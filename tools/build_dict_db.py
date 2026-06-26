"""
词典数据库格式重构脚本（一次性转换工具）

把旧的 mdx(entry, paraphrase=HTML) 单表结构，转换为更高效的
"预解析 JSON" 三表结构。

旧格式（databases/word_details.db，~421MB）
    meta(key, value)
    mdx(entry TEXT, paraphrase TEXT)         -- paraphrase 是 HTML，运行时每次查词都要解析

新格式（databases/word_details_v2.db，预期 ~40MB）
    words(entry PK, data BLOB)               -- data = 预解析 JSON（含全部 WordEntry 字段）
    redirects(entry PK, target)              -- 替代 22 万条 @@@LINK= 占位
    metadata(key PK, html)                   -- @ox3000/@opal_*/@topic_* 词表聚合页（不解析）

为什么只存 JSON、不存 HTML：
  - 实测 paraphrase 的 HTML 中只有约 5%~7% 是结构化内容（音标/释义/例句/词性），
    其余是 CSS class、属性噪声、固定模板，运行时从不读取。
  - 全项目代码路径中，paraphrase 取出后【立刻】被 MdxParser 解析成 WordEntry，
    没有任何地方直接渲染原始 HTML。因此把 HTML 一起存只是 292MB 的纯冗余。
  - 建库时用【同一个】MDXParser 一次性解析为 JSON，运行时直接 json.loads，
    字段语义 100% 一致，且查词零 HTML 解析、更快。

收益：
  - 体积 421MB → ~40MB（去掉 HTML 模板/属性噪声 + 22 万 LINK 文本占位）
  - 查词零 HTML 解析（直接读 JSON），更快
  - entry 主键化，跳转/元数据分离，结构清晰

解析器复用 src/modules/word_lookup.py 的 MDXParser（保证字段语义与运行时一致）。

用法：
    python tools/build_dict_db.py
    python tools/build_dict_db.py --src databases/word_details.db --dst databases/word_details_v2.db
"""

import argparse
import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
import types

# ── 让本脚本可独立运行：绕过 src/modules/__init__.py 对 cv2 等重依赖的导入，
#    直接按文件路径加载 core 和 word_lookup，取出 MDXParser。
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def _load_mdx_parser():
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [os.path.join(ROOT, "src")]
    sys.modules["src"] = src_pkg

    core_spec = importlib.util.spec_from_file_location(
        "src.core", os.path.join(SRC, "core", "__init__.py")
    )
    core_mod = importlib.util.module_from_spec(core_spec)
    sys.modules["src.core"] = core_mod
    core_spec.loader.exec_module(core_mod)

    wl_spec = importlib.util.spec_from_file_location(
        "src.modules.word_lookup", os.path.join(SRC, "modules", "word_lookup.py")
    )
    wl_mod = importlib.util.module_from_spec(wl_spec)
    sys.modules["src.modules.word_lookup"] = wl_mod
    wl_spec.loader.exec_module(wl_mod)

    return wl_mod.MDXParser


MDXParser = _load_mdx_parser()

# 每个 paraphrase 开头都会重复的 CSS/JS 模板，metadata 聚合页入库前剥离
_TEMPLATE_RE = re.compile(
    r'<link rel="stylesheet"[^>]*oald10\.css[^>]*>\s*'
    r'<script[^>]*oald10\.js[^>]*></script>',
    re.IGNORECASE,
)

# 建表 SQL（与 PC/Android 两端共用同一份定义）
#   words.data     = JSON 数组的 UTF-8 字节：[ WordEntry, WordEntry, ... ]
#                    （一个 entry 可能对应多个 WordEntry：一词多义/习语/派生）
#   redirects      = 替代 "paraphrase = @@@LINK=target" 文本占位
#   metadata       = @ox3000 / @opal_* / @topic_* 等词表聚合页（不进主词表）
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS words (
    entry TEXT PRIMARY KEY,
    data  BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_words_entry ON words(entry);

CREATE TABLE IF NOT EXISTS redirects (
    entry  TEXT PRIMARY KEY,
    target TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key  TEXT PRIMARY KEY,
    html TEXT NOT NULL
);
"""


def entry_to_dict(entry):
    """把 WordEntry 转成可 JSON 序列化的 dict（字段与运行时 WordEntry 1:1 对应）"""
    return {
        "headword": entry.headword,
        "phonetics": entry.phonetics,
        "definitions": entry.definitions,
        "chinese_definitions": entry.chinese_definitions,
        "examples": entry.examples,
        "base_form": entry.base_form,
        "pos": entry.pos,
    }


def strip_template(html: str) -> str:
    """剥离每行重复的 oald10.css/oald10.js 模板片段（仅用于 metadata 聚合页）"""
    return _TEMPLATE_RE.sub("", html, count=1).strip()


def build(src_db: str, dst_db: str, batch_size: int = 5000, verbose: bool = True):
    if not os.path.exists(src_db):
        print(f"错误：源库不存在: {src_db}", file=sys.stderr)
        return 1

    src_size = os.path.getsize(src_db)
    if verbose:
        print(f"源库: {src_db}  ({src_size / 1024 / 1024:.1f} MB)")
        print(f"目标: {dst_db}")

    if os.path.exists(dst_db):
        os.remove(dst_db)

    out = sqlite3.connect(dst_db)
    out.executescript(SCHEMA_SQL)
    out.execute("PRAGMA journal_mode = OFF")  # 批量写入，关闭日志提速
    out.execute("PRAGMA synchronous = OFF")

    parser = MDXParser()

    n_words = n_redirects = n_meta = 0
    n_rows = 0
    pending_words = {}  # entry -> list[html]，合并同一 entry 的多行 paraphrase

    src = sqlite3.connect(src_db)
    total = src.execute("SELECT COUNT(*) FROM mdx").fetchone()[0]

    cur = src.execute("SELECT entry, paraphrase FROM mdx")
    t0 = time.time()

    def flush_words():
        """把 pending_words 里累积的多义 entry 一次性写入"""
        nonlocal n_words
        if not pending_words:
            return
        rows_to_insert = []
        for entry, htmls in pending_words.items():
            all_entries = []
            for h in htmls:
                all_entries.extend(parser.parse(h))
            data = json.dumps(
                [entry_to_dict(e) for e in all_entries],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            rows_to_insert.append((entry, data))
        out.executemany(
            "INSERT OR REPLACE INTO words (entry, data) VALUES (?,?)",
            rows_to_insert,
        )
        n_words += len(rows_to_insert)
        pending_words.clear()

    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        redirect_rows = []
        meta_rows = []
        for entry, paraphrase in rows:
            n_rows += 1
            if paraphrase.startswith("@@@LINK="):
                target = paraphrase[len("@@@LINK="):].strip()
                redirect_rows.append((entry, target))
            elif entry.startswith("@"):
                # 词表/主题聚合页（@ox3000/@opal_*/@topic_*），不解析、剥离模板后原样存
                meta_rows.append((entry, strip_template(paraphrase)))
            else:
                pending_words.setdefault(entry, []).append(paraphrase)
        if redirect_rows:
            out.executemany(
                "INSERT OR REPLACE INTO redirects (entry, target) VALUES (?,?)",
                redirect_rows,
            )
            n_redirects += len(redirect_rows)
        if meta_rows:
            out.executemany(
                "INSERT OR REPLACE INTO metadata (key, html) VALUES (?,?)",
                meta_rows,
            )
            n_meta += len(meta_rows)
        flush_words()
        out.commit()

        if verbose and (n_rows % 50000 == 0 or n_rows == total):
            elapsed = time.time() - t0
            print(
                f"  进度 {n_rows}/{total}  ({n_rows/total*100:.1f}%)  "
                f"用时 {elapsed:.0f}s  "
                f"words={n_words} redirects={n_redirects} metadata={n_meta}"
            )

    src.close()

    # user_version = 2：词典格式版本号（1=旧 mdx 单表，2=新三表）
    out.execute("PRAGMA user_version = 2")
    out.execute("ANALYZE")
    out.execute("VACUUM")  # 压缩空闲页
    out.commit()
    out.close()

    dst_size = os.path.getsize(dst_db)
    if verbose:
        print("\n===== 转换完成 =====")
        print(f"words    表: {n_words:>8} 行")
        print(f"redirects表: {n_redirects:>8} 行")
        print(f"metadata 表: {n_meta:>8} 行")
        print(f"源库大小: {src_size/1024/1024:.1f} MB")
        print(f"新库大小: {dst_size/1024/1024:.1f} MB")
        ratio = dst_size / src_size * 100 if src_size else 0
        saved = (src_size - dst_size) / 1024 / 1024
        print(f"压缩比 : {ratio:.1f}%  (节省 {saved:.1f} MB)")
        print("user_version = 2")
    return 0


def main():
    ap = argparse.ArgumentParser(description="把旧 mdx 单表词典转换为新三表格式")
    ap.add_argument(
        "--src",
        default=os.path.join(ROOT, "databases", "word_details.db"),
        help="源库路径（默认 databases/word_details.db）",
    )
    ap.add_argument(
        "--dst",
        default=os.path.join(ROOT, "databases", "word_details_v2.db"),
        help="目标库路径（默认 databases/word_details_v2.db）",
    )
    ap.add_argument("--quiet", action="store_true", help="少打印日志")
    args = ap.parse_args()
    return build(args.src, args.dst, verbose=not args.quiet)


if __name__ == "__main__":
    sys.exit(main())
