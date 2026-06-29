import logging
import os

from core.functions import BASE_OLLAMA_URL, OLLAMA_IP, mongo_db_client, AI_IP

from ..types.data_keeper import ProviderData

logger = logging.getLogger(__name__)

class DataStore:
    def __init__(self):
        
        self.available_providers: dict[str, ProviderData] = {}
        self._other_data = {}

        self._init_data()

    def _init_data(self):
        # available providers
        self.available_providers: dict[str, ProviderData] = {
            'openrouter': {
                'base_url': "https://openrouter.ai/api/v1",
                'api_key': os.getenv('openrouter_KEY')
            },
            'zhipu': {
                'base_url': 'https://open.bigmodel.cn/api/paas/v4/',
                'api_key': os.getenv('zhipuAI_KEY')
            },
            'ollama': {
                'base_url': f'{BASE_OLLAMA_URL}/v1',
                'api_key': 'ollama'
            },
            'gemini': {
                'base_url': "https://generativelanguage.googleapis.com/v1beta/openai/",
                'api_key': os.getenv("gemini_KEY")
            },
            'cerebras':{
                'base_url': 'https://api.cerebras.ai/v1',
                'api_key': os.getenv('cerebras_KEY')
            },
            'lmstudio': {
                'base_url': f'http://{OLLAMA_IP}:1239/v1',
                'api_key': 'hi'
            },
            'ai-local': {
                'base_url': f'http://{AI_IP}:4000/v1',
                'api_key': ''
            }
        }
        for v in self.available_providers.values():
            v['models'] = []


DATA_STORE = DataStore()