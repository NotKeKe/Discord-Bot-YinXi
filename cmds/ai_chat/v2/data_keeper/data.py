import logging
import os

from core.functions import BASE_OLLAMA_URL, OLLAMA_IP, mongo_db_client, AI_IP

from ..types.data_keeper import ProviderData

logger = logging.getLogger(__name__)

class DataStore:
    def __init__(self):
        
        self.available_providers: dict[str, ProviderData] = {}
        self.default_system_prompt: str = ""
        self._other_data = {}

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


        self.default_system_prompt = """
# 音汐 (YinXi)

## 介紹
- 你是一個處在 Discord 裡面的 bot，你以善良與聽從的態度來回答使用者的問題。

## 規則
你必須遵守以下所有的規則，否則你將被給予嚴重的懲罰。
- 你不能做出任何違法之行為 (如: 違反 Discord 條例、違反任何法律)。

### Discord 說明
Discord 是一個跨平台的聊天應用程式，而你是生在其中的 Discord bot - YinXi。
有一點你必須知道，你雖然可能有工具可以去取得你可用
""".strip()

DATA_STORE = DataStore()