import requests
import json
from config import config

class SiliconFlowAI:
    def __init__(self):
        self.api_key = config.get_api_key()
        self.model = config.get_model()
        self.base_url = "https://api.siliconflow.cn/v1"
    
    def _make_request(self, endpoint, data):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/{endpoint}',
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None
    
    def judge_word_form(self, word, context):
        prompt = f"""请分析以下单词在给定语境中的词形：

单词：{word}
语境：{context}

请判断：
1. 这个单词是原形（base form）还是变形形式（如过去式、复数等）？
2. 如果是变形形式，原形是什么？
3. 在这个语境中，应该使用原形还是变形形式？

请用JSON格式回答，格式如下：
{{
    "is_base_form": true/false,
    "base_form": "原形单词",
    "recommended_form": "推荐使用的词形",
    "reason": "判断理由"
}}"""
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'stream': False
        }
        
        result = self._make_request('chat/completions', data)
        
        if result and 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        
        return None
    
    def analyze_context(self, word, definitions, context):
        prompt = f"""请分析以下语境，为单词选择最合适的释义：

单词：{word}
语境：{context}
可选释义：
{json.dumps(definitions, ensure_ascii=False, indent=2)}

请根据语境选择最合适的释义，并说明理由。
请用JSON格式回答，格式如下：
{{
    "best_definition_index": 0,
    "reason": "选择理由"
}}"""
        
        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'stream': False
        }
        
        result = self._make_request('chat/completions', data)
        
        if result and 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        
        return None

ai_service = SiliconFlowAI()
