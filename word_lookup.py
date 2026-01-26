import sqlite3
import os
import re
from html.parser import HTMLParser
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from ai_service import ai_service
from config import config

try:
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    print("警告: nltk未安装，词形还原功能将不可用。请运行 'pip install nltk' 来启用此功能。")


@dataclass
class WordEntry:
    """单词条目数据类"""
    headword: str
    phonetics: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    chinese_definitions: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    base_form: Optional[str] = None
    pos: Optional[str] = None  # Part of Speech (词性)


@dataclass
class LookupResult:
    """查词结果数据类"""
    success: bool
    word: str
    phonetic: str = "N/A"
    definitions: List[str] = field(default_factory=list)
    base_form: Optional[str] = None
    pos: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    message: Optional[str] = None
    all_entries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'success': self.success,
            'word': self.word,
        }

        if self.success:
            result.update({
                'phonetic': self.phonetic,
                'definitions': self.definitions,
                'base_form': self.base_form or self.word,
                'pos': self.pos,
                'examples': self.examples
            })
            if self.all_entries:
                result['all_entries'] = self.all_entries
        else:
            result['message'] = self.message

        return result


class MDXParser(HTMLParser):
    """MDX格式HTML解析器"""

    def __init__(self):
        super().__init__()
        self.reset()
        self.entries: List[WordEntry] = []
        self._init_current_entry()

    def _init_current_entry(self):
        """初始化当前条目数据"""
        self.headword: Optional[str] = None
        self.phonetics: List[str] = []
        self.definitions: List[str] = []
        self.chinese_definitions: List[str] = []
        self.examples: List[str] = []
        self.base_form: Optional[str] = None
        self.current_pos: Optional[str] = None
        self.current_tag: Optional[str] = None
        self.current_class: str = ""
        self.current_def: Optional[str] = None
        self.current_chinese: Optional[str] = None
        self.current_example: Optional[str] = None

        # 状态标志
        self.in_headword = False
        self.in_phon = False
        self.in_def = False
        self.in_chinese = False
        self.in_example = False
        self.in_xref = False
        self.in_base_form = False
        self.capture_text = False
        self.skip_nested = False
        self.just_finished_def = False
        self.entry_class: Optional[str] = None

    def _save_current_entry(self):
        """保存当前条目到entries列表"""
        if self.headword:
            entry = WordEntry(
                headword=self.headword,
                phonetics=self.phonetics.copy(),
                definitions=self.definitions.copy(),
                chinese_definitions=self.chinese_definitions.copy(),
                examples=self.examples.copy(),
                base_form=self.base_form,
                pos=self.current_pos
            )
            self.entries.append(entry)

    def _reset_current_entry(self):
        """重置当前条目数据"""
        self.headword = None
        self.phonetics = []
        self.definitions = []
        self.chinese_definitions = []
        self.examples = []
        self.base_form = None
        self.current_pos = None
        self.just_finished_def = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        self.current_class = attrs_dict.get('class', '')

        if tag == 'div' and 'entry' in self.current_class:
            self._save_current_entry()
            self._reset_current_entry()
            self.entry_class = 'entry'

        elif tag == 'h1' and 'headword' in self.current_class:
            self.in_headword = True
            self.capture_text = True
            self.skip_nested = False

        elif tag == 'span' and 'pos' in self.current_class:
            self.in_phon = False
            self.capture_text = True
            self.skip_nested = False

        elif tag == 'span' and 'phon' in self.current_class:
            self.in_phon = True
            self.capture_text = True
            self.skip_nested = False

        elif tag == 'span' and 'def' in self.current_class and not self.skip_nested:
            self.in_def = True
            self.current_def = ''
            self.capture_text = True

        elif tag == 'chn' and self.just_finished_def:
            self.in_chinese = True
            self.current_chinese = ''
            self.capture_text = True

        elif tag == 'span' and self.current_class == 'x' and not self.skip_nested:
            self.in_example = True
            self.current_example = ''
            self.capture_text = True

        elif tag == 'span' and 'xrefs' in self.current_class:
            self.in_xref = True
            self.capture_text = False

        elif tag == 'span' and self.current_class == 'xh' and self.in_xref:
            self.in_base_form = True
            self.capture_text = True

        elif tag == 'a' and 'Ref' in attrs_dict.get('class', ''):
            self.capture_text = False

    def handle_endtag(self, tag: str):
        if tag == 'div' and self.entry_class == 'entry':
            self._save_current_entry()
            self.entry_class = None

        elif tag == 'h1' and self.in_headword:
            self.in_headword = False
            self.capture_text = False
            self.skip_nested = False

        elif tag == 'span' and 'pos' in self.current_class:
            self.current_pos = self.current_data.strip() if hasattr(self, 'current_data') else None
            self.capture_text = False

        elif tag == 'span' and self.in_phon:
            self.in_phon = False
            self.capture_text = False

        elif tag == 'span' and self.in_def:
            if self.current_def:
                self.definitions.append(self.current_def.strip())
                self.just_finished_def = True
            self.in_def = False
            self.capture_text = False

        elif tag == 'chn' and self.in_chinese:
            if self.current_chinese:
                self.chinese_definitions.append(self.current_chinese.strip())
                self.just_finished_def = False
            self.in_chinese = False
            self.capture_text = False

        elif tag == 'span' and self.in_xref:
            self.in_xref = False
            self.capture_text = False

        elif tag == 'a' and 'Ref' in self.current_class:
            self.capture_text = False

        elif tag == 'span' and self.in_base_form:
            self.in_base_form = False
            self.capture_text = False

        elif tag == 'span' and self.in_example:
            if self.current_example:
                self.examples.append(self.current_example.strip())
            self.in_example = False
            self.capture_text = False

    def handle_data(self, data: str):
        self.current_data = data
        if self.capture_text:
            if self.in_headword and not self.headword:
                self.headword = data.strip()
            elif self.in_phon:
                phonetic = data.strip()
                if phonetic and phonetic not in self.phonetics:
                    self.phonetics.append(phonetic)
            elif self.in_def and self.current_def is not None:
                self.current_def += data
            elif self.in_chinese and self.current_chinese is not None:
                self.current_chinese += data
            elif self.in_base_form:
                self.base_form = data.strip()
            elif self.in_example and self.current_example is not None:
                self.current_example += data

    def parse(self, html_content: str) -> List[WordEntry]:
        """解析HTML内容，返回单词条目列表"""
        self.reset()
        self.entries = []
        self._init_current_entry()

        # 检查是否是MDX链接格式
        if html_content.startswith('@@@LINK='):
            link_target = html_content[8:].strip()
            return [WordEntry(
                headword=link_target,
                base_form=link_target
            )]

        self.feed(html_content)

        # 处理最后一个条目
        self._save_current_entry()

        return self.entries if self.entries else []


class WordLookup:
    """单词查询类"""

    def __init__(self):
        self.db_dir = os.path.join(os.path.dirname(__file__), 'databases')
        self.word_details_path = os.path.join(self.db_dir, 'word_details.db')
        self.lemmatizer = self._init_lemmatizer()

    def _init_lemmatizer(self) -> Optional[WordNetLemmatizer]:
        """初始化词形还原器"""
        if not NLTK_AVAILABLE:
            return None

        try:
            lemmatizer = WordNetLemmatizer()
            # 验证WordNet数据是否可用
            try:
                wordnet.synsets('test')
            except LookupError:
                print("警告: 未找到WordNet数据，请运行以下命令安装:")
                print("import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')")
                return None
            return lemmatizer
        except Exception as e:
            print(f"初始化词形还原器失败: {e}")
            return None

    def check_database_exists(self) -> None:
        """检查数据库文件是否存在"""
        if not os.path.exists(self.word_details_path):
            raise FileNotFoundError(f"Word database not found at {self.word_details_path}")

    def _execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Optional[Any]:
        """执行数据库查询"""
        conn = sqlite3.connect(self.word_details_path)
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            return None
        finally:
            conn.close()

    def word_exists(self, word: str) -> bool:
        """检查单词是否存在于数据库中"""
        result = self._execute_query(
            'SELECT entry FROM mdx WHERE entry = ?',
            (word,),
            fetch_one=True
        )
        return result is not None

    def get_entry_html(self, word: str) -> Optional[str]:
        """获取单词的HTML内容"""
        result = self._execute_query(
            'SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1',
            (word,),
            fetch_one=True
        )
        return result[0] if result else None

    def get_all_entries_html(self, word: str) -> List[str]:
        """获取单词的所有HTML内容"""
        results = self._execute_query(
            'SELECT paraphrase FROM mdx WHERE entry = ?',
            (word,),
            fetch_all=True
        )
        return [result[0] for result in results] if results else []

    def parse_entry(self, html_content: str) -> List[WordEntry]:
        """解析HTML内容为单词条目"""
        parser = MDXParser()
        return parser.parse(html_content)

    def get_word_entries(self, word: str) -> List[WordEntry]:
        """获取单词的所有条目"""
        html_contents = self.get_all_entries_html(word)
        entries = []
        for html_content in html_contents:
            parsed = self.parse_entry(html_content)
            entries.extend(parsed)
        return entries

    def get_base_form_from_db(self, word: str) -> Optional[str]:
        """从数据库获取单词的基本形式"""
        html_content = self.get_entry_html(word)
        if not html_content:
            return None

        entries = self.parse_entry(html_content)
        if entries and entries[0].base_form:
            return entries[0].base_form

        return None

    def get_word_base_form_nltk(self, word: str) -> Optional[str]:
        """使用NLTK获取单词的基本形式"""
        if not NLTK_AVAILABLE or not self.lemmatizer:
            return None

        word_exists = self.word_exists(word)

        # 尝试不同的词性进行词形还原
        pos_tags = ['n', 'v', 'a', 'r']
        for pos in pos_tags:
            lemma = self.lemmatizer.lemmatize(word, pos)
            if lemma != word and not word_exists and self.word_exists(lemma):
                return lemma

        # 默认词形还原
        default_lemma = self.lemmatizer.lemmatize(word)
        if default_lemma != word and not word_exists and self.word_exists(default_lemma):
            return default_lemma

        return None

    def get_word_base_form_simple(self, word: str) -> Optional[str]:
        """使用简单规则获取单词的基本形式"""
        word_exists = self.word_exists(word)

        # 特殊不规则动词
        special_cases = {
            'ran': 'run', 'bit': 'bite', 'ate': 'eat', 'drove': 'drive',
            'saw': 'see', 'fell': 'fall', 'gave': 'give', 'knew': 'know',
            'thought': 'think', 'threw': 'throw', 'came': 'come', 'went': 'go',
            'bought': 'buy', 'brought': 'bring', 'caught': 'catch',
            'fought': 'fight', 'taught': 'teach', 'sought': 'seek',
            'bent': 'bend', 'bound': 'bind', 'built': 'build',
            'dealt': 'deal', 'felt': 'feel', 'held': 'hold',
            'kept': 'keep', 'led': 'lead', 'lost': 'lose',
            'meant': 'mean', 'paid': 'pay', 'sold': 'sell',
            'sent': 'send', 'spent': 'spend', 'stood': 'stand',
            'understood': 'understand', 'won': 'win', 'wound': 'wind'
        }

        word_lower = word.lower()
        if word_lower in special_cases:
            base = special_cases[word_lower]
            if not word_exists and self.word_exists(base):
                return base

        # 动词过去式 (-ed)
        if word.endswith('ed') and len(word) > 3:
            base = word[:-2]
            if len(base) > 1 and base[-1] == base[-2]:
                base = base[:-1]
            elif len(base) > 1 and base.endswith('i'):
                base = base[:-1] + 'y'

            if not word_exists and self.word_exists(base):
                return base

        # 复数形式 (-es, -s)
        if word.endswith('es') and len(word) > 3:
            base = word[:-2]
            if not word_exists and self.word_exists(base):
                return base
        elif word.endswith('s') and len(word) > 2 and not word.endswith('ss'):
            base = word[:-1]
            if not word_exists and self.word_exists(base):
                return base

        # 动词现在分词 (-ing)
        if word.endswith('ing') and len(word) > 4:
            base = word[:-3]
            if len(base) > 1 and base[-1] == base[-2]:
                base = base[:-1]

            if not word_exists and self.word_exists(base):
                return base
            elif not word_exists and self.word_exists(base + 'e'):
                return base + 'e'

        # 形容词比较级/最高级 (-er/-est)
        if word.endswith('er') and len(word) > 3:
            base = word[:-2]
            if not word_exists and self.word_exists(base):
                return base
            elif not word_exists and self.word_exists(base + 'e'):
                return base + 'e'
        elif word.endswith('est') and len(word) > 4:
            base = word[:-3]
            if not word_exists and self.word_exists(base):
                return base
            elif not word_exists and self.word_exists(base + 'e'):
                return base + 'e'

        return None

    def get_word_base_form(self, word: str) -> Optional[str]:
        """获取单词的基本形式"""
        # 优先使用数据库链接信息
        base_form = self.get_base_form_from_db(word)
        if base_form:
            return base_form

        # 然后尝试NLTK
        if NLTK_AVAILABLE and self.lemmatizer:
            base_form = self.get_word_base_form_nltk(word)
            if base_form:
                return base_form

        # 最后尝试简单规则
        return self.get_word_base_form_simple(word)

    def tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        return re.findall(r'\b\w+\b', text)

    def calculate_similarity(self, context: str, entry: WordEntry) -> float:
        """计算语境与条目的相似度"""
        context_tokens = set(self.tokenize(context))

        # 使用中文释义和例句计算相似度
        definition_text = ' '.join(entry.chinese_definitions) + ' ' + ' '.join(entry.examples)
        definition_tokens = set(self.tokenize(definition_text))

        if not context_tokens or not definition_tokens:
            return 0.0

        intersection = context_tokens & definition_tokens
        union = context_tokens | definition_tokens

        return len(intersection) / len(union) if union else 0.0

    def find_best_match(self, entries: List[WordEntry], context: str) -> Optional[WordEntry]:
        """根据语境找到最佳匹配的条目"""
        if not entries:
            return None

        if not context or len(entries) == 1:
            return entries[0]

        # 计算每个条目的相似度分数
        scored_entries = [
            (self.calculate_similarity(context, entry), entry)
            for entry in entries
        ]

        # 按相似度排序，返回最高分
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return scored_entries[0][1]

    def _resolve_word_form(self, word: str) -> Tuple[str, Optional[str]]:
        """
        解析单词形式，返回(查找用词, 基本形式)
        优先级: 数据库链接 > NLTK > 简单规则
        """
        # 检查单词是否存在
        if self.word_exists(word):
            base_form = self.get_base_form_from_db(word)
            return word, base_form

        # 尝试获取基本形式
        base_form = self.get_word_base_form(word)
        if base_form:
            return base_form, base_form

        return word, None

    def _get_phonetics(self, entry: WordEntry, base_entry: Optional[WordEntry] = None) -> List[str]:
        """获取音标，优先使用基本形式的音标"""
        if base_entry and base_entry.phonetics:
            return base_entry.phonetics
        return entry.phonetics

    def _format_phonetic(self, phonetics: List[str], max_count: int = 2) -> str:
        """格式化音标显示"""
        if not phonetics:
            return "N/A"
        return ', '.join(phonetics[:max_count])

    def lookup(self, word: str, context: str = "", use_ai: bool = True) -> LookupResult:
        """
        查询单词

        Args:
            word: 要查询的单词
            context: 语境描述
            use_ai: 是否使用AI判断词形

        Returns:
            LookupResult: 查询结果
        """
        self.check_database_exists()

        word = word.strip()
        context = context.strip()

        if not word:
            return LookupResult(success=False, word="", message="请输入要查询的单词")

        # 解析单词形式
        lookup_word, base_form = self._resolve_word_form(word)

        # 如果找不到基本形式，返回错误
        if not self.word_exists(lookup_word):
            return LookupResult(
                success=False,
                word=word,
                message=f'数据库中未找到单词 "{word}"'
            )

        # AI判断词形（可选）
        if use_ai and config.get_api_key():
            try:
                ai_result = ai_service.judge_word_form(lookup_word, context)
                if ai_result and ai_result.get('recommended_form'):
                    lookup_word = ai_result['recommended_form']
            except Exception as e:
                print(f"AI判断失败，继续使用默认逻辑: {e}")

        # 获取所有条目
        entries = self.get_word_entries(lookup_word)
        if not entries:
            return LookupResult(
                success=False,
                word=word,
                message=f'未找到单词 "{word}" 的释义'
            )

        # 根据语境选择最佳条目
        best_entry = self.find_best_match(entries, context)

        # 获取基本形式的条目（用于音标等）
        base_entry = None
        if base_form and base_form != lookup_word:
            base_entries = self.get_word_entries(base_form)
            if base_entries:
                base_entry = base_entries[0]

        # 获取音标
        phonetics = self._get_phonetics(best_entry, base_entry)

        # 优先使用中文释义，如果没有则使用英文释义
        definitions = best_entry.chinese_definitions if best_entry.chinese_definitions else best_entry.definitions

        # 构建结果
        result = LookupResult(
            success=True,
            word=lookup_word,
            phonetic=self._format_phonetic(phonetics),
            definitions=definitions,
            base_form=base_form or lookup_word,
            pos=best_entry.pos,
            examples=best_entry.examples
        )

        return result

    def get_all_definitions(self, word: str) -> LookupResult:
        """获取单词的所有释义"""
        self.check_database_exists()

        word = word.strip()

        # 解析单词形式
        lookup_word, base_form = self._resolve_word_form(word)

        if not self.word_exists(lookup_word):
            return LookupResult(
                success=False,
                word=word,
                message=f'数据库中未找到单词 "{word}"'
            )

        # 获取所有条目
        entries = self.get_word_entries(lookup_word)

        # 转换为字典格式
        all_entries = []
        for entry in entries:
            all_entries.append({
                'headword': entry.headword,
                'phonetics': entry.phonetics,
                'definitions': entry.definitions,
                'chinese_definitions': entry.chinese_definitions,
                'examples': entry.examples,
                'pos': entry.pos
            })

        result = LookupResult(
            success=True,
            word=lookup_word,
            base_form=base_form or lookup_word,
            all_entries=all_entries
        )

        return result


def main():
    """命令行交互界面"""
    print("=" * 60)
    print("单词查询系统 - 基于语境的释义匹配")
    print("=" * 60)
    print()

    try:
        lookup = WordLookup()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return

    while True:
        print("\n请选择操作:")
        print("1. 查询单词（输入语境）")
        print("2. 查看单词所有释义")
        print("3. 退出")

        choice = input("\n请输入选项 (1/2/3): ").strip()

        if choice == '1':
            word = input("请输入英文单词: ").strip()
            context = input("请输入语境描述: ").strip()

            result = lookup.lookup(word, context)

            print("\n" + "-" * 60)
            if result.success:
                print(f"单词: {result.word}")
                if result.base_form and result.base_form != result.word:
                    print(f"原形: {result.base_form}")
                if result.pos:
                    print(f"词性: {result.pos}")
                print(f"音标: {result.phonetic}")
                print(f"\n中文释义:")
                for i, definition in enumerate(result.definitions, 1):
                    print(f"  {i}. {definition}")
                if result.examples:
                    print(f"\n例句:")
                    for i, example in enumerate(result.examples[:3], 1):
                        print(f"  {i}. {example}")
            else:
                print(f"错误: {result.message}")
            print("-" * 60)

        elif choice == '2':
            word = input("请输入英文单词: ").strip()

            result = lookup.get_all_definitions(word)

            print("\n" + "-" * 60)
            if result.success:
                print(f"单词: {result.word}")
                if result.base_form and result.base_form != result.word:
                    print(f"原形: {result.base_form}")
                print(f"\n共有 {len(result.all_entries)} 个条目:\n")

                for i, entry in enumerate(result.all_entries, 1):
                    print(f"{i}. {entry['headword']}")
                    if entry.get('pos'):
                        print(f"   词性: {entry['pos']}")
                    print(f"   音标: {', '.join(entry['phonetics']) if entry['phonetics'] else 'N/A'}")
                    print(f"   中文释义:")
                    for j, definition in enumerate(entry['chinese_definitions'] if entry['chinese_definitions'] else entry['definitions'], 1):
                        print(f"     {j}. {definition}")
                    if entry['examples']:
                        print(f"   例句:")
                        for j, example in enumerate(entry['examples'][:2], 1):
                            print(f"     {j}. {example}")
                    print()
            else:
                print(f"错误: {result.message}")
            print("-" * 60)

        elif choice == '3':
            print("再见!")
            break


if __name__ == '__main__':
    main()
