import orjson
from discord.ext import commands
from typing import Optional, cast, Iterable, Callable, Any
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCallUnion,
    ChatCompletionMessageFunctionToolCall,
)

from ..types.chater import *
from ..ai_model.detector import ModelDetector
from ..data_keeper.clients import get_openai_client
from ..tool.main import load_skills, get_tool_descriptions

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
            system_prompt='',
            is_enable_tools=True,
            history=[]
        )


    async def _handle_completion(self, response: ChatCompletion) -> CompletionResponse:
        message = response.choices[0].message

        result = message.content or ""

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
        self._infos.system_prompt = prompt

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

            resp: ChatCompletion = await client.chat.completions.create(
                model=self._infos.meta.model.model,
                messages=cast(Iterable[ChatCompletionMessageParam], messages),
                tools=get_tool_descriptions() if is_enable_tools else None, # type: ignore
            )

            if not resp.choices:
                raise ValueError('AI has no response (no response.choices[0])')

            comp_resp = await self._handle_completion(resp)

            # 沒有工具調用就跳出迴圈
            if not comp_resp.tool_calls:
                break

            assistant_message, tool_messages = await self._handle_tool_call(comp_resp.tool_calls)
            self._infos.history.append(assistant_message)
            self._infos.history.extend(tool_messages)

            if tool_messages and all(tool_message.content == "no result" for tool_message in tool_messages):
                no_result_rounds += 1
                if no_result_rounds == 3:
                    self._infos.history.append(
                        UserMessage(
                            content="This message is from system: "
                            "<>The tool has produced no output for 3 consecutive times. "
                            "Try canceling the next tool call and inform the user that the tool is unavailable.</>"
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
            result=comp_resp.result,
            infos=self._infos
        )