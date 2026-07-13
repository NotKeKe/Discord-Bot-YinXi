from pydantic import BaseModel, Field
from typing import Annotated, Literal
from enum import StrEnum
from discord.ext import commands
from datetime import datetime

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
    activated_tools: list[str] = Field(default_factory=list)

    def to_openai_messages(self) -> list[dict]:
        return [m.model_dump(mode="json", exclude_none=True) for m in self.history]



class StatusEnum(StrEnum):
    INIT = "init"
    RECEVING_THINK = "Receving stream think"
    RECEVING_CONTENT = "Receving stream content"
    RECEVING_TOOL_CALLS = "Receving tool calls"
    TOOL_CALLING = "Tool calling" # 工具正在被調用
    TOOL_CALLING_DONE = "Tool calling done"
    DONE = "done"
    ERROR = "error"

class Status(BaseModel):
    status: StatusEnum
    detail_string: str = ""
    update_time: datetime

    def format_time(self):
        return self.update_time.strftime("%Y-%m-%d %a %H:%M:%S %z")


class ChatResponse(BaseModel):
    think: str
    result: str
    infos: Infos



class CompletionResponse(BaseModel):
    think: str
    result: str
    tool_calls: list[ChatCompletionMessageToolCallUnion] | None
    token_count: int