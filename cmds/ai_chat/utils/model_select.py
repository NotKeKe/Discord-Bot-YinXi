from openai import AsyncOpenAI
from typing import Union
import logging
import aiofiles
import orjson

from .client import AsyncClient
from .config import MODEL_TEMP_PATH

logger = logging.getLogger(__name__)


PROVIDERS = {
    'openrouter': AsyncClient.openrouter,
    'lmstudio': AsyncClient.lmstudio,
    'ollama': AsyncClient.ollama,
    'gemini': AsyncClient.gemini,
    'cerebras': AsyncClient.cerebras,
    'zhipu': AsyncClient.zhipu
}

async def model_select(model: str) -> Union[AsyncOpenAI, None]:
    async with aiofiles.open(MODEL_TEMP_PATH, 'r', encoding='utf-8') as f:
        data = orjson.loads(await f.read())

        for key in data:
            if model in set(data[key]):
                return PROVIDERS[key]
        
    return None