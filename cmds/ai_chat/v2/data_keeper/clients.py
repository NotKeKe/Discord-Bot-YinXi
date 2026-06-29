from openai import AsyncOpenAI
from .data import DATA_STORE

OPENAI_CLIENTS = {
    k: AsyncOpenAI(base_url=str(v['base_url']), api_key=str(v['api_key'])) 
        for k, v in DATA_STORE.available_providers.items()
}

def get_openai_client(provider: str) -> AsyncOpenAI:
    return OPENAI_CLIENTS[provider] 