from pydantic import BaseModel, Field
from typing import Annotated, Literal
from enum import StrEnum
from discord.ext import commands

from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCallUnion
from openai.types.chat.chat_completion_content_part_param import ChatCompletionContentPartParam


class Model(BaseModel):
    provider: str = "zhipu"
    model: str = "glm-4-flash"



class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str

class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str | None = None
    tool_calls: list[ChatCompletionMessageToolCallUnion] | None = None

class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str

class ToolMessage(BaseModel):
    role: Literal["tool"] = "tool"
    name: str # function name
    content: str
    tool_call_id: str

SingleHistory = Annotated[
    UserMessage | AssistantMessage | SystemMessage | ToolMessage,
    Field(discriminator="role"),
]

class Meta(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    model: Model
    ctx: commands.Context

class Infos(BaseModel):
    meta: Meta
    history: list[SingleHistory]
    system_prompt: str
    is_enable_tools: bool

    def to_openai_messages(self) -> list[dict]:
        return [m.model_dump(mode="json", exclude_none=True) for m in self.history]


class StatusEnum(StrEnum):
    RECEVING = "receiving"
    DONE = "done"
    ERROR = "error"

class Status(BaseModel):
    status: str
    readable: str



class ChatResponse(BaseModel):
    think: str
    result: str
    infos: Infos



class CompletionResponse(BaseModel):
    think: str
    result: str
    tool_calls: list[ChatCompletionMessageToolCallUnion] | None
    token_count: int