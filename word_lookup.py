import sqlite3
import os
import re
from html.parser import HTMLParser
from collections import Counter
from ai_service import ai_service
from config import config

try:
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    print("警告: nltk未安装，词形还原功能将不可用。请运行 'pip install nltk' 来启用此功能。")

class MDXParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.headword = None
        self.phonetics = []
        self.definitions = []
        self.chinese_definitions = []
        self.examples = []
        self.base_form = None
        self.current_tag = None
        self.current_class = None
        self.current_def = None
        self.current_chinese = None
        self.current_example = None
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
        self.current_pos = None
        self.entries = []
        self.entry_class = None
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        self.current_class = attrs_dict.get('class', '')
        
        if tag == 'div' and 'entry' in self.current_class:
            # 开始新的条目
            if self.headword:
                self.entries.append({
                    'headword': self.headword,
                    'phonetics': self.phonetics.copy(),
                    'definitions': self.definitions.copy(),
                    'chinese_definitions': self.chinese_definitions.copy(),
                    'examples': self.examples.copy(),
                    'base_form': self.base_form,
                    'pos': self.current_pos
                })
                self.headword = None
                self.phonetics = []
                self.definitions = []
                self.chinese_definitions = []
                self.examples = []
                self.base_form = None
                self.current_pos = None
            self.entry_class = 'entry'
        
        if tag == 'h1' and 'headword' in self.current_class:
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
    
    def handle_endtag(self, tag):
        if tag == 'div' and self.entry_class == 'entry':
            # 结束条目
            if self.headword:
                self.entries.append({
                    'headword': self.headword,
                    'phonetics': self.phonetics.copy(),
                    'definitions': self.definitions.copy(),
                    'chinese_definitions': self.chinese_definitions.copy(),
                    'examples': self.examples.copy(),
                    'base_form': self.base_form,
                    'pos': self.current_pos
                })
            self.entry_class = None
        
        if tag == 'h1' and self.in_headword:
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
    
    def handle_data(self, data):
        self.current_data = data
        if self.capture_text:
            if self.in_headword:
                if not self.headword:
                    self.headword = data.strip()
            elif self.in_phon:
                phonetic = data.strip()
                if phonetic and phonetic not in self.phonetics:
                    self.phonetics.append(phonetic)
            elif self.in_def:
                if self.current_def is not None:
                    self.current_def += data
            elif self.in_chinese:
                if self.current_chinese is not None:
                    self.current_chinese += data
            elif self.in_base_form:
                self.base_form = data.strip()
            elif self.in_example:
                if self.current_example is not None:
                    self.current_example += data

class WordLookup:
    def __init__(self):
        self.db_dir = os.path.join(os.path.dirname(__file__), 'databases')
        self.word_details_path = os.path.join(self.db_dir, 'word_details.db')
        
        # 初始化词形还原器
        if NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
                # 尝试加载必要的NLTK数据
                from nltk.corpus import wordnet
                try:
                    wordnet.synsets('test')
                except LookupError:
                    print("警告: 未找到WordNet数据，请运行以下命令安装:")
                    print("import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')")
            except Exception as e:
                print(f"初始化词形还原器失败: {e}")
                self.lemmatizer = None
        else:
            self.lemmatizer = None
    
    def check_database_exists(self):
        if not os.path.exists(self.word_details_path):
            raise FileNotFoundError(f"Word database not found at {self.word_details_path}")
    
    def parse_entry(self, html_content):
        parser = MDXParser()
        
        # 检查是否是MDX链接格式
        if html_content.startswith('@@@LINK='):
            link_target = html_content[8:].strip()
            return [{
                'headword': link_target,
                'phonetics': [],
                'definitions': [],
                'chinese_definitions': [],
                'examples': [],
                'base_form': link_target,
                'pos': None
            }]
        
        parser.feed(html_content)

        # 不从xrefs中提取base_form，因为那是同义词，不是词形还原的基本形式
        # 基本形式应该只从MDX链接格式中获取

        # 如果解析器中有多个条目，返回所有条目
        if parser.entries:
            return parser.entries
        
        # 如果只有一个条目，返回单个条目的列表
        if parser.headword:
            return [{
                'headword': parser.headword,
                'phonetics': parser.phonetics,
                'definitions': parser.definitions,
                'chinese_definitions': parser.chinese_definitions,
                'examples': parser.examples,
                'base_form': parser.base_form,
                'pos': parser.current_pos
            }]
        
        return []
    
    def get_word_base_form_nltk(self, word):
        """使用NLTK获取单词的基本形式"""
        if not NLTK_AVAILABLE or not self.lemmatizer:
            return None
        
        # 首先验证输入的词本身是否在数据库中
        word_exists = self.word_exists(word)
        
        # 尝试不同的词性进行词形还原
        pos_tags = ['n', 'v', 'a', 'r']  # 名词、动词、形容词、副词
        for pos in pos_tags:
            lemma = self.lemmatizer.lemmatize(word, pos)
            if lemma != word and not word_exists and self.word_exists(lemma):  # 只有当变形词不存在但基词存在时才返回基词
                return lemma
        
        # 如果按不同词性都没找到，尝试默认的词形还原
        default_lemma = self.lemmatizer.lemmatize(word)
        if default_lemma != word and not word_exists and self.word_exists(default_lemma):
            return default_lemma
            
        return None

    def get_word_base_form_simple(self, word):
        """简单的词形还原规则，不依赖NLTK"""
        # 首先验证输入的词本身是否在数据库中
        word_exists = self.word_exists(word)
        
        # 动词过去式和过去分词
        if word.endswith('ed') and len(word) > 3:
            # 尝试去掉-ed
            base = word[:-2]
            # 处理双写辅音的情况，如stopped -> stop
            if len(base) > 1 and base[-1] == base[-2]:
                base = base[:-1]
            # 处理以-y结尾的词，变-ied结尾，如tried -> try
            elif len(base) > 1 and base.endswith('i'):
                base = base[:-1] + 'y'
            
            # 只有当变形词不存在但基词存在时，才认为这是一个变形词
            if not word_exists and self.word_exists(base):
                return base
                
            # 特殊情况处理
            special_cases = {
                'ran': 'run',
                'bit': 'bite',
                'ate': 'eat',
                'drove': 'drive',
                'saw': 'see',
                'fell': 'fall',
                'gave': 'give',
                'knew': 'know',
                'thought': 'think',
                'threw': 'throw',
                'came': 'come',
                'went': 'go',
                'bought': 'buy',
                'brought': 'bring',
                'caught': 'catch',
                'fought': 'fight',
                'taught': 'teach',
                'sought': 'seek',
                'bent': 'bend',
                'bound': 'bind',
                'built': 'build',
                'dealt': 'deal',
                'felt': 'feel',
                'held': 'hold',
                'kept': 'keep',
                'led': 'lead',
                'lost': 'lose',
                'meant': 'mean',
                'paid': 'pay',
                'sold': 'sell',
                'sent': 'send',
                'spent': 'spend',
                'stood': 'stand',
                'understood': 'understand',
                'won': 'win',
                'wound': 'wind',
                'refused': 'refuse',
                'used': 'use'  # pronounced differently when past tense vs noun/adjective
            }
            
            if word.lower() in special_cases:
                potential_base = special_cases[word.lower()]
                if not word_exists and self.word_exists(potential_base):
                    return potential_base
        
        # 复数形式
        if word.endswith('es') and len(word) > 3:
            base = word[:-2]
            if not word_exists and self.word_exists(base):
                return base
        elif word.endswith('s') and len(word) > 2 and not word.endswith('ss'):
            base = word[:-1]
            if not word_exists and self.word_exists(base):
                return base
        
        # 动词现在分词和形容词
        if word.endswith('ing') and len(word) > 4:
            base = word[:-3]  # 去掉ing
            # 检查是否是双写字母结尾的ing形式
            if len(base) > 1 and base[-1] == base[-2]:
                base = base[:-1]
                
            if not word_exists and self.word_exists(base):
                return base
            # 也尝试加上e（如果动词是以e结尾+ing的）
            elif not word_exists and self.word_exists(base + 'e'):
                return base + 'e'
        
        # 形容词比较级和最高级
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
    
    def get_word_base_form(self, word):
        """获取单词的基本形式，优先使用数据库链接信息，然后是NLTK，最后是简单规则"""
        # 首先检查数据库中是否有链接信息
        base_form = self.get_base_form(word)
        if base_form:
            return base_form
        
        # 然后尝试NLTK
        if NLTK_AVAILABLE and self.lemmatizer:
            base_form = self.get_word_base_form_nltk(word)
            if base_form:
                return base_form
        
        # 最后尝试简单规则
        return self.get_word_base_form_simple(word)
    
    def _execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
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
    
    def word_exists(self, word):
        result = self._execute_query(
            'SELECT entry FROM mdx WHERE entry = ?',
            (word,),
            fetch_one=True
        )
        return result is not None
    
    def get_entry(self, word):
        result = self._execute_query(
            'SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1',
            (word,),
            fetch_one=True
        )

        if result:
            html_content = result[0]
            parsed = self.parse_entry(html_content)
            
            # 如果解析结果中有多个条目，返回第一个
            if parsed:
                return parsed[0] if isinstance(parsed, list) else parsed

        return None
    
    def get_all_entries(self, word):
        results = self._execute_query(
            'SELECT paraphrase FROM mdx WHERE entry = ?',
            (word,),
            fetch_all=True
        )

        entries = []
        for result in results:
            html_content = result[0]
            parsed = self.parse_entry(html_content)
            
            # 如果解析结果中有多个条目，直接添加到列表
            if parsed:
                if isinstance(parsed, list):
                    entries.extend(parsed)
                else:
                    entries.append(parsed)

        return entries
    
    def get_base_form(self, word):
        result = self._execute_query(
            'SELECT paraphrase FROM mdx WHERE entry = ? LIMIT 1',
            (word,),
            fetch_one=True
        )

        if result:
            html_content = result[0]
            parsed = self.parse_entry(html_content)

            # 如果解析结果中有多个条目，检查第一个条目的base_form
            if parsed:
                entry = parsed[0] if isinstance(parsed, list) else parsed
                if entry.get('base_form'):
                    return entry['base_form']

        return None
    
    def tokenize(self, text):
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def calculate_similarity(self, context, definition_data):
        context_tokens = set(self.tokenize(context))
        
        definition_text = ' '.join(definition_data['chinese_definitions']) + ' ' + ' '.join(definition_data['examples'])
        definition_tokens = set(self.tokenize(definition_text))
        
        if not context_tokens or not definition_tokens:
            return 0.0
        
        intersection = context_tokens & definition_tokens
        union = context_tokens | definition_tokens
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        return jaccard_similarity
    
    def find_best_match(self, word, context):
        entries = self.get_all_entries(word)
        
        if not entries:
            return None
        
        scored_entries = []
        for entry in entries:
            score = self.calculate_similarity(context, entry)
            scored_entries.append((score, entry))
        
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        
        return scored_entries[0][1]
    
    def lookup(self, word, context):
        self.check_database_exists()
        
        word = word.strip()
        context = context.strip()
        
        if not word:
            return {
                'success': False,
                'message': 'Please enter a word'
            }
        
        # 首先尝试查找原始单词
        original_word_exists = self.word_exists(word)
        
        # 如果原始单词存在，则使用原始单词
        if original_word_exists:
            use_word = word
        else:
            # 尝试查找基本形式
            base_form = self.get_word_base_form(word)
            if base_form:
                # 使用基本形式进行查找
                use_word = base_form
            else:
                return {
                    'success': False,
                    'message': f'Word "{word}" not found in the database'
                }

        base_form = self.get_base_form(use_word)
        
        ai_result = None
        if config.get_api_key():
            ai_result = ai_service.judge_word_form(use_word, context)
        
        if ai_result and ai_result.get('recommended_form'):
            use_word = ai_result['recommended_form']
            ai_reason = ai_result.get('reason', '')
        elif base_form:
            if base_form != use_word:
                context_tokens = set(self.tokenize(context))
                word_lower = use_word.lower()

                if word_lower not in context_tokens:
                    use_word = base_form
        
        best_match = self.find_best_match(use_word, context)
        
        if best_match:
            phonetics_to_use = []
            if base_form and base_form != use_word:
                base_entry = self.get_entry(base_form)
                if base_entry and base_entry['phonetics']:
                    phonetics_to_use = base_entry['phonetics']
                else:
                    phonetics_to_use = best_match['phonetics']
            else:
                phonetics_to_use = best_match['phonetics']
            
            result = {
                'success': True,
                'word': word,  # 使用用户输入的原始单词
                'base_form': base_form if base_form and base_form != use_word else None,
                'phonetic': ', '.join(phonetics_to_use) if phonetics_to_use else 'N/A',
                'definitions': best_match['chinese_definitions'] if best_match['chinese_definitions'] else best_match['definitions'],
                'examples': best_match['examples']
            }
            
            if ai_result:
                result['ai_analysis'] = {
                    'recommended_form': ai_result.get('recommended_form'),
                    'reason': ai_result.get('reason')
                }
            
            return result
        else:
            return {
                'success': False,
                'message': f'No definition found for word "{word}"'
            }
    
    def get_all_definitions(self, word):
        self.check_database_exists()
        
        word = word.strip()
        
        if not self.word_exists(word):
            return {
                'success': False,
                'message': f'Word "{word}" not found in the database'
            }
        
        entries = self.get_all_entries(word)
        
        return {
            'success': True,
            'word': word,
            'entries': entries
        }
    
    def lookup_base_form_only(self, word, context=''):
        self.check_database_exists()
        
        word = word.strip()
        context = context.strip()
        
        if not word:
            return {
                'success': False,
                'message': 'Please enter a word'
            }
        
        # 首先尝试查找原始单词
        original_word_exists = self.word_exists(word)
        
        # 如果原始单词存在，则使用原始单词
        if original_word_exists:
            use_word = word
        else:
            # 尝试查找基本形式
            base_form = self.get_word_base_form(word)
            if base_form:
                # 使用基本形式进行查找
                use_word = base_form
            else:
                return {
                    'success': False,
                    'message': f'Word "{word}" not found in database'
                }
        
        # 获取基本形式（如果存在）
        base_form = self.get_word_base_form(use_word)
        final_word = base_form if base_form else use_word
        
        # 获取原型的所有条目
        entries = self.get_all_entries(final_word)
        
        if entries:
            # 根据语境找到最合适的释义
            if context:
                best_match = self.find_best_match(final_word, context)
                if best_match:
                    chinese_defs = best_match['chinese_definitions'][:1] if best_match['chinese_definitions'] else []
                    phonetics_to_use = best_match['phonetics']
                else:
                    chinese_defs = entries[0]['chinese_definitions'][:1] if entries[0]['chinese_definitions'] else []
                    phonetics_to_use = entries[0]['phonetics']
            else:
                # 没有语境时，使用第一个释义
                chinese_defs = entries[0]['chinese_definitions'][:1] if entries[0]['chinese_definitions'] else []
                phonetics_to_use = entries[0]['phonetics']
            
            result = {
                'success': True,
                'word': word,
                'base_form': final_word,
                'phonetic': ', '.join(phonetics_to_use[:2]) if phonetics_to_use else 'N/A',
                'definitions': chinese_defs
            }
            
            return result
        else:
            return {
                'success': False,
                'message': f'No definition found for word "{word}"'
            }

def main():
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
            if result['success']:
                print(f"单词: {result['word']}")  # 这里显示用户输入的原始单词
                if result['base_form']:
                    print(f"原形: {result['base_form']}")
                print(f"音标: {result['phonetic']}")
                print(f"\n中文释义:")
                for i, definition in enumerate(result['definitions'], 1):
                    print(f"  {i}. {definition}")
                if result['examples']:
                    print(f"\n例句:")
                    for i, example in enumerate(result['examples'], 1):
                        print(f"  {i}. {example}")
                if 'ai_analysis' in result:
                    print(f"\nAI分析:")
                    print(f"  推荐词形: {result['ai_analysis']['recommended_form']}")
                    print(f"  判断理由: {result['ai_analysis']['reason']}")
            else:
                print(f"错误: {result['message']}")
            print("-" * 60)
        
        elif choice == '2':
            word = input("请输入英文单词: ").strip()
            
            result = lookup.get_all_definitions(word)
            
            print("\n" + "-" * 60)
            if result['success']:
                print(f"单词: {result['word']}")
                print(f"\n共有 {len(result['entries'])} 个条目:\n")
                for i, entry in enumerate(result['entries'], 1):
                    print(f"{i}. {entry['headword']}")
                    print(f"   音标: {', '.join(entry['phonetics']) if entry['phonetics'] else 'N/A'}")
                    print(f"   中文释义:")
                    for j, definition in enumerate(entry['chinese_definitions'] if entry['chinese_definitions'] else entry['definitions'], 1):
                        print(f"     {j}. {definition}")
                    if entry['examples']:
                        print(f"   例句:")
                        for j, example in enumerate(entry['examples'], 1):
                            print(f"     {j}. {example}")
                    print()
            else:
                print(f"错误: {result['message']}")
            print("-" * 60)

if __name__ == '__main__':
    main()