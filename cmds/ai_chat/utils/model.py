import logging

from .client import AsyncClient
from .config import db_client

logger = logging.getLogger(__name__)

async def fetch_models():
    try:
        openrouter_models = [model.id for model in (await AsyncClient.openrouter.models.list()).data 
                             if model.id.endswith('free') or model.id == 'openrouter/horizon-beta']
        # logger.info(f'openrouter: {openrouter_models}')
    except Exception as e:
        logger.error(f'Cannot fetch openrouter models: {e}')
        openrouter_models = []

    try:
        # zhipu_models = [model.id for model in (await AsyncClient.zhipu.models.list()).data]
        zhipu_models = [
            'glm-4-flash',
            'glm-4.5-flash',
            'glm-z1-flash',
            'glm-4-flash-250414',
            'glm-4.7-flash',
            'glm-4.6v-flash',
            'glm-4.1v-thinking-flash'
        ]
        # logger.info(f'zhipu: {zhipu_models}')
    except Exception as e:
        logger.error(f'Cannot fetch zhipu models: {e}')
        zhipu_models = []

    try:
        ollama_models = [model.id for model in (await AsyncClient.ollama.models.list()).data]
        # logger.info(f'ollama: {ollama_models}')
    except Exception as e:
        logger.error(f'Cannot fetch ollama models: {e}')
        ollama_models = []

    try:
        # gemini_models = [model.id for model in (await AsyncClient.gemini.models.list()).data]
        gemini_models = [
            'gemini-2.5-pro',
            'gemini-2.5-flash',
            'gemma-3-27b-it',
        ]
        # logger.info(f'gemini: {gemini_models}')
    except Exception as e:
        logger.error(f'Cannot fetch gemini models: {e}')
        gemini_models = []

    try:
        cerebras_models = [model.id for model in (await AsyncClient.cerebras.models.list()).data]
        # logger.info(f'cerebras: {cerebras_models}')
    except Exception as e:
        logger.error(f'Cannot fetch cerebras models: {e}')
        cerebras_models = []

    try:
        lmstudio_models = [model.id for model in (await AsyncClient.lmstudio.models.list()).data]
        # logger.info(f'lmstudio: {lmstudio_models}')
    except Exception as e:
        logger.error(f'Cannot fetch lmstudio models: {e}')
        lmstudio_models = []

    data = {
        'openrouter': openrouter_models,
        'zhipu': zhipu_models,
        'ollama': ollama_models,
        'gemini': gemini_models,
        'cerebras': cerebras_models,
        'lmstudio': lmstudio_models
    }
    
    db = db_client['aichat_available_models']
    collection = db['models']

    _id = 'model_setting'

    await collection.find_one_and_replace(
        {'_id': _id},
        data,
        upsert=True
    )

        # async with aiofiles.open(MODEL_TEMP_PATH, 'wb') as f:
        #     await f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        #     logger.info('successfully write models')