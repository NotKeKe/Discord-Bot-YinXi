from pydantic import BaseModel
from typing import Literal
from discord.ext import commands

from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCallUnion

class Model(BaseModel):
    provider: str = 'zhipu'
    model: str = 'glm-4-flash'


class ToolCall(BaseModel):
    id: str
    type: str
    function: dict

class SingleHistory(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_calls: list

class Meta(BaseModel):
    model: Model
    ctx: commands.Context

class Infos(BaseModel):
    meta: Meta
    history: list[SingleHistory]

    def get_format_history(self) -> list[dict]:
        return [{'role': h.role, 'content': h.content} for h in self.history]



class ChatResponse(BaseModel):
    think: str
    result: str
    infos: Infos


class CompletionResponse(BaseModel):
    think: str
    result: str
    tool_calls: list[ChatCompletionMessageToolCallUnion]
    token_count: int