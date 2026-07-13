import orjson
from discord.ext import commands
from typing import Optional, cast, Iterable, Callable, Any
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCallUnion,
    ChatCompletionMessageFunctionToolCall,
    Function as ToolFunction,
)

from ..types.chater import *
from ..ai_model.detector import ModelDetector
from ..data_keeper.clients import get_openai_client
from ..tool.main import load_skills, get_tool_descriptions
from ..prompts import get_default_system_prompt

from .utils import get_think, clean_text
from cmds.ai_chat.v1.tools import tool_map
from core.functions import is_async

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
            ),
            system_prompt=get_default_system_prompt(ctx),
            is_enable_tools=True,
            history=[]
        )

    def change_system_prompt(self, system_prompt: str):
        self._infos.system_prompt = system_prompt

    async def _handle_stream(self, stream: AsyncStream[ChatCompletionChunk]) -> CompletionResponse:
        content_chunks: list[str] = []
        reasoning_chunks: list[str] = []
        tool_calls_deltas: dict[int, dict] = {}
        finish_reason: str | None = None
        total_tokens = -1

        async for chunk in stream:
            if not chunk.choices:
                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens or -1
                continue

            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason or finish_reason

            if delta.content is not None:
                content_chunks.append(delta.content)

            reasoning = getattr(delta, 'reasoning_content', None)
            if reasoning is not None:
                reasoning_chunks.append(reasoning)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index
                    if index not in tool_calls_deltas:
                        tool_calls_deltas[index] = {
                            "id": "",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls_deltas[index]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_deltas[index]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_deltas[index]["function"]["arguments"] += tc.function.arguments

            if chunk.usage and chunk.usage.total_tokens:
                total_tokens = chunk.usage.total_tokens

        result = "".join(content_chunks)
        think = "".join(reasoning_chunks)

        if not think:
            think = get_think(result)
            result = clean_text(result)

        tool_calls = None
        if finish_reason == "tool_calls" and tool_calls_deltas:
            tool_calls = [
                ChatCompletionMessageFunctionToolCall(
                    id=tc["id"],
                    type="function",
                    function=ToolFunction(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    ),
                )
                for tc in (tool_calls_deltas[i] for i in sorted(tool_calls_deltas))
            ]

        return CompletionResponse(
            think=think,
            result=result.strip(),
            tool_calls=cast(list[ChatCompletionMessageToolCallUnion] | None, tool_calls),
            token_count=total_tokens,
        )


    def change_model(self, model: str):
        self._infos.meta.model = ModelDetector.detect_to_model(model)

    async def _handle_tool_call(
        self,
        tool_calls: list[ChatCompletionMessageToolCallUnion]
    ) -> tuple[AssistantMessage, list[ToolMessage]]:
        assistant_message = AssistantMessage(
            content=None,
            tool_calls=tool_calls
        )

        tool_messages: list[ToolMessage] = []
        for tool_call in tool_calls:
            tool_call_id = ""
            function_name = "unknown"
            function_response = "no result"

            if isinstance(tool_call, ChatCompletionMessageFunctionToolCall) and tool_call.id and tool_call.function and tool_call.function.name:
                tool_call_id = tool_call.id
                function_name = tool_call.function.name

                try:
                    function_to_call = cast(Callable[..., Any] | None, tool_map.get(function_name))
                    if not function_to_call:
                        function_response = f"Function '{function_name}' not found in tool map."
                    else:
                        function_args = orjson.loads(tool_call.function.arguments)
                        if not isinstance(function_args, dict):
                            raise TypeError("Function arguments must be a dictionary.")

                        if is_async(function_to_call):
                            function_response = await function_to_call(**function_args)
                        else:
                            function_response = function_to_call(**function_args)

                except orjson.JSONDecodeError:
                    function_response = f"Error: Failed to parse arguments for '{function_name}'. Arguments must be valid JSON."
                except (TypeError, ValueError) as e:
                    function_response = f"Error: Failed to call '{function_name}'. Details: {e}"
                except Exception as e:
                    function_response = f"Error: An unexpected error occurred while calling '{function_name}'. Details: {e}"

            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=str(function_response)
                )
            )

        return assistant_message, tool_messages

    async def chat(
        self, 
        ctx: commands.Context,
        is_enable_tools: bool = True
    ) -> ChatResponse:
        await load_skills()

        # 不同訊息會有不同的 commands.Context 物件
        self._infos.meta.ctx = ctx
        self._infos.is_enable_tools = is_enable_tools

        client = get_openai_client(self._infos.meta.model.provider)

        self._infos.history.append(
            UserMessage(
                content=f'`{self._infos.meta.ctx.author.global_name}` said: 「{self._infos.meta.ctx.message.content}」'
            )
        )

        call_times = 0
        max_tool_calls = 10
        no_result_rounds = 0
        comp_resp: CompletionResponse | None = None
        run_last = False # 如果工具調用到第10輪，就將這個設為 True，並停用工具，讓 AI 做最終回覆

        while call_times < max_tool_calls or run_last:
            messages: list[dict] = []
            if self._infos.system_prompt:
                messages.append(SystemMessage(content=self._infos.system_prompt).model_dump(mode="json", exclude_none=True))
            messages.extend(self._infos.to_openai_messages())

            # call openai api (stream)
            stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create( # type: ignore
                model=self._infos.meta.model.model,
                messages=cast(Iterable[ChatCompletionMessageParam], messages),
                tools=get_tool_descriptions() if is_enable_tools else None,
                stream=True,
                stream_options={"include_usage": True},
            )

            comp_resp = await self._handle_stream(stream)

            # 沒有工具調用就跳出迴圈
            if not comp_resp.tool_calls:
                self._infos.history.append(AssistantMessage(content=comp_resp.result))
                break

            assistant_message, tool_messages = await self._handle_tool_call(comp_resp.tool_calls)
            self._infos.history.append(assistant_message)
            self._infos.history.extend(tool_messages)

            if tool_messages and all(tool_message.content == "no result" for tool_message in tool_messages):
                no_result_rounds += 1
                if no_result_rounds == 3:
                    self._infos.history.append(
                        UserMessage(
                            content="This message is from system: \n"
                            "<>\nThe tool has produced no output for 3 consecutive times. \n"
                            "Try canceling the next tool call and inform the user that the tool is unavailable.\n</>"
                        )
                    )
            else:
                no_result_rounds = 0

            call_times += 1

            if call_times >= max_tool_calls: # 超過工具調用次數了
                run_last = True
                is_enable_tools = False
                

        if comp_resp is None:
            raise ValueError('AI has no response')

        return ChatResponse(
            think=comp_resp.think,
            result=comp_resp.result.strip(),
            infos=self._infos
        )