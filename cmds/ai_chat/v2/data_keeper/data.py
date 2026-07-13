import logging
import os

from core.functions import BASE_OLLAMA_URL, OLLAMA_IP, mongo_db_client, AI_IP

from ..types.data_keeper import ProviderData
from ..tool import ALL_SKILLS, is_skill_loaded

logger = logging.getLogger(__name__)

class DataStore:
    def __init__(self):
        
        self.available_providers: dict[str, ProviderData] = {}
        self.other_data = { # 由其他地方 init 的 data
            'skills': ALL_SKILLS
        }

        self._init_data()

    def _init_data(self):
        # available providers
        _keys = {
            'openrouter': os.getenv('openrouter_KEY'),
            'zhipu': os.getenv('zhipuAI_KEY'),
            'ollama': 'ollama',
            'gemini': os.getenv('gemini_KEY'),
            'cerebras': os.getenv('cerebras_KEY'),
            'lmstudio': 'hi',
            'ai-local': ''
        }

        self.available_providers: dict[str, ProviderData] = {}
        for name, key in list(_keys.items()):
            if key is None:
                continue
            self.available_providers[name] = {
                'api_key': key,
                'base_url': {
                    'openrouter': "https://openrouter.ai/api/v1",
                    'zhipu': 'https://open.bigmodel.cn/api/paas/v4/',
                    'ollama': f'{BASE_OLLAMA_URL}/v1',
                    'gemini': "https://generativelanguage.googleapis.com/v1beta/openai/",
                    'cerebras': 'https://api.cerebras.ai/v1',
                    'lmstudio': f'http://{OLLAMA_IP}:1239/v1',
                    'ai-local': f'http://{AI_IP}:4000/v1'
                }[name],
                'models': []
            }

DATA_STORE = DataStore()