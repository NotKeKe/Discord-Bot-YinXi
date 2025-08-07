from discord.ext import commands
import asyncio
from typing import Tuple

from ..chat.chat import Chat
from ..utils.config import chat_human_system_prompt

model = 'cerebras:qwen-3-235b-a22b-instruct-2507'

async def get_example_response(user_prompt: str) -> str:
    # TODO
    ex_resp = ''
    return (
'''
## 回應範例
{ex_resp}
'''.format(ex_resp=ex_resp)
)

async def chat_human_chat(ctx: commands.Context, prompt: str, history: list, urls: list = None) -> Tuple[str, str]:
    client = Chat(model, chat_human_system_prompt + (await get_example_response(prompt)), ctx)

    think, result, complete_history = await client.chat(
        prompt, 
        history=history,
        url=urls
    )

    return think, result