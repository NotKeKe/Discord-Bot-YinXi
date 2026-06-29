from discord.ext import commands
import asyncio
from typing import Tuple
import logging

from ..chat.chat import Chat
from ..utils.config import db_client, base_system_prompt

logger = logging.getLogger(__name__)

db_key = 'aichannel_chat_history'
_id = 'ai_channel_setting'
db = db_client[db_key]

async def get_history(ctx: commands.Context) -> list:
    collection = db[str(ctx.channel.id)]

    data = await collection.find_one({"messages": {"$exists": True}})
    if data:
        return data.get('messages', [])

    return []

async def save_history(ctx: commands.Context, history: list):
    try:
        collection = db[str(ctx.channel.id)]

        await collection.update_one(
        filter={"messages": {"$exists": True}},
        update={
            "$set": {
                "messages": history
            }
        }, 
        upsert=True)
    except:
        logger.error('Error accured at save_history', exc_info=True)


async def ai_channel_chat(ctx: commands.Context, prompt: str, model: str, system_prompt: str = None, urls: list = None) -> Tuple[str, str, list]:
    system_prompt = system_prompt or base_system_prompt
    client = Chat(model, system_prompt, ctx)

    history = await get_history(ctx)

    think, result, complete_history = await client.chat(
        f'`{(ctx.author.global_name)}` said: 「{prompt}」', 
        history=history,
        url=urls
    )

    asyncio.create_task(save_history(ctx, complete_history))

    return think, result, complete_history