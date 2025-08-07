import os
from motor.motor_asyncio import AsyncIOMotorClient

from core.functions import BASE_OLLAMA_URL, OLLAMA_IP, mongo_db_client

openrouter_KEY = os.getenv('openrouter_KEY')
zhipu_KEY = os.getenv('zhipuAI_KEY')
hugging_KEY = os.getenv('huggingFace_KEY')
gemini_KEY = os.getenv("gemini_KEY")
cerebras_KEY = os.getenv('cerebras_KEY')

base_url_options = {
    'openrouter': {
        'base_url': "https://openrouter.ai/api/v1",
        'api_key': openrouter_KEY
    },
    'zhipu': {
        'base_url': 'https://open.bigmodel.cn/api/paas/v4/',
        'api_key': zhipu_KEY
    },
    'ollama': {
        'base_url': f'{BASE_OLLAMA_URL}/v1',
        'api_key': 'ollama'
    },
    'gemini': {
        'base_url': "https://generativelanguage.googleapis.com/v1beta/openai/",
        'api_key': gemini_KEY
    },
    'cerebras':{
        'base_url': 'https://api.cerebras.ai/v1',
        'api_key': cerebras_KEY
    },
    'lmstudio': {
        'base_url': f'http://{OLLAMA_IP}:1239/v1',
        'api_key': 'hi'
    }
}

MODEL_TEMP_PATH = './cmds/ai_chat/temp/models.json'

with open('./cmds/ai_chat/data/prompts/base_system_prompt.md', 'r', encoding='utf-8') as f:
    base_system_prompt = f.read()

with open('./cmds/ai_chat/data/prompts/chat_human_prompt_1.md', 'r', encoding='utf-8') as f:
    chat_human_system_prompt = f.read()

with open('./cmds/ai_chat/data/prompts/summarize_history_system_prompt.md', 'r', encoding='utf-8') as f:
    summarize_history_system_prompt = (f.read()).strip()

db_client = mongo_db_client