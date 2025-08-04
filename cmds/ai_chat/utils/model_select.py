from openai import AsyncOpenAI
from typing import Union
import logging
import aiofiles
import orjson
from motor.motor_asyncio import AsyncIOMotorClient

# from cmds.ai_three import availble_models

from .client import AsyncClient
from .config import MODEL_TEMP_PATH, MONGO_URL

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
    try:
        db_client = AsyncIOMotorClient(MONGO_URL)
        db = db_client['aichat_available_models']
        collection = db['models']

        _id = 'model_setting'

        result = await collection.find_one({'_id': _id})
    finally:
        if db_client:
            db_client.close()

    for key in result:
        if model in set(result[key]):
            return PROVIDERS[key]
        
    return None