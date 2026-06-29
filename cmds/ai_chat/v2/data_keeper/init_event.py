import openai

from .data import DATA_STORE
from .clients import OPENAI_CLIENTS

_run = False

async def _init_available_models():
    for provider in DATA_STORE.available_providers.keys():
        client = OPENAI_CLIENTS[provider]
        models = await client.models.list()

        DATA_STORE.available_providers[provider]['models'] = [model.id for model in models.data]

async def init_event():
    """應該要在 bot 上的 on_ready 執行

    Raises:
        RuntimeError: _description_
    """    
    global _run

    if _run:
        raise RuntimeError("init_event already ran")

    await _init_available_models()



    if not _run:
        _run = True