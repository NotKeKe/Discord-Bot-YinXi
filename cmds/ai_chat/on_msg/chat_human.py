from discord.ext import commands
import asyncio
from typing import Tuple
from openai import RateLimitError

from ..chat.chat import Chat
from ..utils.config import chat_human_system_prompt

model1 = 'cerebras:qwen-3-235b-a22b-instruct-2507'
model2 = 'zhipu:glm-4.7-flash'

async def get_example_response(user_prompt: str) -> str:
    # TODO
    ex_resp = ''
    return (
'''
## 回應範例
{ex_resp}
'''.format(ex_resp=ex_resp)
)

async def chat_human_chat(ctx: commands.Context, prompt: str, history: list, urls: list | None = None, is_retry: bool = False) -> Tuple[str, str]:
    try:
        client = Chat(
            model1 if not is_retry else model2, # 回退機制
            chat_human_system_prompt + (await get_example_response(prompt)), 
            ctx
        )

        think, result, complete_history = await client.chat(
            prompt, 
            history=history,
            url=urls
        )
    except RateLimitError as e:
        if is_retry:
            try:
                raise e # re raise
            finally:
                return '', 'Rate limit exceeded. Please try again later.'
                
        return await chat_human_chat(ctx, prompt, history, urls, is_retry=True)

    return think, result