from pydantic import BaseModel, Field
from typing import Annotated, Literal
from discord.ext import commands

from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCallUnion
from openai.types.chat.chat_completion_content_part_param import ChatCompletionContentPartParam


class Model(BaseModel):
    provider: str = "zhipu"
    model: str = "glm-4-flash"



class UserMessage(BaseModel):
    role: Literal["user"]
    content: str

class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[ChatCompletionMessageToolCallUnion] | None = None

class SystemMessage(BaseModel):
    role: Literal["system"]
    content: str

class ToolMessage(BaseModel):
    role: Literal["tool"]
    name: str # function name
    content: str
    tool_call_id: str

SingleHistory = Annotated[
    UserMessage | AssistantMessage | SystemMessage | ToolMessage,
    Field(discriminator="role"),
]

class Meta(BaseModel):
    model: Model
    ctx: commands.Context

class Infos(BaseModel):
    meta: Meta
    history: list[SingleHistory]

    def to_openai_messages(self) -> list[dict]:
        return [m.model_dump(exclude_none=True) for m in self.history]



class ChatResponse(BaseModel):
    think: str
    result: str
    infos: Infos



class CompletionResponse(BaseModel):
    think: str
    result: str
    tool_calls: list[ChatCompletionMessageToolCallUnion]
    token_count: int