import os
import json
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = Path(__file__).parent / 'config.json'
        self.config = self.load_config()
    
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'siliconflow_api_key': '',
            'siliconflow_model': 'deepseek-ai/DeepSeek-V3'
        }
    
    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_api_key(self):
        api_key = self.config.get('siliconflow_api_key', '')
        if not api_key:
            api_key = os.getenv('SILICONFLOW_API_KEY', '')
        return api_key
    
    def get_model(self):
        return self.config.get('siliconflow_model', 'deepseek-ai/DeepSeek-V3')
    
    def set_api_key(self, api_key):
        self.config['siliconflow_api_key'] = api_key
        self.save_config()
    
    def set_model(self, model):
        self.config['siliconflow_model'] = model
        self.save_config()

config = Config()
