import openai
from discord.ext import commands
from typing import Optional, cast, Iterable
from openai.types.chat import ChatCompletionChunk, ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCallUnion

from ..types.chater import *
from ..ai_model.detector import ModelDetector
from ..data_keeper.clients import get_openai_client

from .utils import get_think, clean_text

class Chater:
    def __init__(
        self, 
        ctx: commands.Context, 
        model: Optional[str] = None
    ):
        self._infos = Infos(
            meta=Meta(
                model=ModelDetector.detect_to_model(model) if model else Model(),
                ctx=ctx,
                system_prompt=""
            ),
            history=[]
        )


    async def _handle_tool_call(self, tool_calls: list[ChatCompletionMessageToolCallUnion], infos: Infos):
        ...

    async def _handle_completion(self, response: ChatCompletion) -> CompletionResponse:
        if not response or not response.choices:
            raise ValueError('AI has no response (no response or no response.choices[0])')

        message = response.choices[0].message


        if message.content:
            result = message.content

        think = ""
        if (hasattr(message, 'reasoning_content')):
            think = str(message.reasoning_content)
        elif (hasattr(message, 'reasoning')):
            think = str(message.reasoning)
        
        # 如果 think 是被包含在 result 裡面，到這裡才會做處理
        # 這裡再 clean_text 是為了避免在正常情況下，刪到 LLM 原本就要輸出的東西
        if not think:
            think = get_think(result)
            result = clean_text(result)

        total_tokens = response.usage.total_tokens if response.usage else -1

        return CompletionResponse(
            think=think,
            result=result.strip(),
            tool_calls=message.tool_calls,
            token_count=total_tokens
        )
        

    def change_system_prompt(self, prompt: str):
        self._infos.meta.system_prompt = prompt

    def change_model(self, model: str):
        self._model = ModelDetector.detect_to_model(model)

    async def chat(self, ctx: commands.Context) -> ChatResponse:
        # 不同訊息會有不同的 commands.Context 物件
        self._infos.meta.ctx = ctx
        
        client = get_openai_client(self._model.provider)

        self._infos.history.append(
            UserMessage(
                content=f'`{self._infos.meta.ctx.author.global_name}` said: 「{self._infos.meta.ctx.message.content}」'
            )
        )

        while True:
            resp = await client.chat.completions.create(
                model=self._model.model,
                messages=cast(Iterable[ChatCompletionMessageParam], self._infos.to_openai_messages()),
            )

            if not resp.choices:
                raise ValueError('AI has no response (no response.choices[0])')

            comp_resp = await self._handle_completion(resp)

            # 沒有工具調用就跳出迴圈
            if not comp_resp.tool_calls:
                break

            await self._handle_tool_call(comp_resp.tool_calls, self._infos)

        return ChatResponse(

        )