from discord import app_commands, Interaction
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient

from core.functions import MONGO_URL, UnixToReadable

async def history_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    try:
        db_client = AsyncIOMotorClient(MONGO_URL)
        db = db_client['aichat_chat_history']
        collection = db[str(interaction.user.id)]
        
        data = [
            (d.get('title', ''), d.get('createAt', 0)) 
            async for d in collection.find() 
        ]
            
        if current:
            data = [(title, time) for title, time in data if current.lower().strip() in title.lower().strip() and title != '']

        data.sort(key=lambda x: x[1], reverse=True)

        # 限制最多回傳 25 個結果
        return [app_commands.Choice(name=f'{title} ({UnixToReadable(time)})', value=title) for title, time in data[:25] if title != '']
    finally:
        if db_client:
            db_client.close()

async def model_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    try:
        db_client = AsyncIOMotorClient(MONGO_URL)
        db = db_client['aichat_available_models']
        collection = db['models']

        _id = 'model_setting'

        result = await collection.find_one({'_id': _id})

        models = [model for provider, item in dict(result).items() if provider != '_id' for model in item]

        if current:
            models = [m for m in models if current.lower().strip() in m.lower().strip()]
            models.sort()
        
        return [app_commands.Choice(name=model, value=model) for model in set(models[:25])]

    finally:
        if db_client:
            db_client.close()