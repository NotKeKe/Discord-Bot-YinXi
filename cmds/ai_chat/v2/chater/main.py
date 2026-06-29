import openai
from discord.ext import commands
from typing import Optional, cast, Iterable
from openai.types.chat import ChatCompletionChunk, ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCallUnion

from ..types.chater import *
from ..ai_model.detector import ModelDetector
from ..data_keeper.clients import get_openai_client

class Chater:
    def __init__(
        self, 
        ctx: commands.Context, 
        model: Optional[str] = None
    ):
        self._infos = Infos(
            meta=Meta(
                model=ModelDetector.detect_to_model(model) if model else Model(),
                ctx=ctx
            ),
            history=[]
        )


    async def _handle_tool_call(self, tool_calls: list[ChatCompletionMessageToolCallUnion], infos: Infos):
        

    async def _handle_completion(self, response: ChatCompletion) -> CompletionResponse:
        ...
        

    def change_system_prompt(self):
        ...

    def change_model(self, model: str):
        self._model = ModelDetector.detect_to_model(model)

    async def chat(self) -> ChatResponse:
        client = get_openai_client(self._model.provider)

        self._infos.history.append(
            SingleHistory(
                role='user',
                content=self._infos.meta.ctx.message.content
            )
        )

        while True:
            resp = await client.chat.completions.create(
                model=self._model.model,
                messages=cast(Iterable[ChatCompletionMessageParam], self._infos.get_format_history()),
            )

            if not resp.choices:
                raise ValueError('AI has no response (no response.choices[0])')

            comp_resp = await self._handle_completion(resp)
            if comp_resp.tool_calls:
                await self._handle_tool_call(comp_resp.tool_calls)

        return ChatResponse(

        )