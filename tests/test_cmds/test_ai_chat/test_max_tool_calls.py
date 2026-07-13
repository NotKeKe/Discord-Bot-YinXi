import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord.ext import commands
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

# Prevent real clients module from executing at import time
fake_clients = MagicMock()
fake_clients.get_openai_client = MagicMock()
sys.modules["cmds.ai_chat.v2.data_keeper.clients"] = fake_clients

# Prevent real v1 tools from loading
sys.modules["cmds.ai_chat.v1.tools"] = MagicMock(tool_map={"test_tool": MagicMock()})

from cmds.ai_chat.v2.chater.main import Chater


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=commands.Context)
    ctx.author = MagicMock()
    ctx.author.name = "TestUser"
    ctx.author.global_name = "TestUser"
    ctx.guild = None
    ctx.message = MagicMock()
    ctx.message.content = "Hello"
    return ctx


def _make_response(content: str, tool_calls=None):
    mock = MagicMock()
    mock.choices = [
        MagicMock(
            message=MagicMock(
                content=content,
                tool_calls=tool_calls,
                reasoning_content=None,
                reasoning=None,
            )
        )
    ]
    mock.usage = MagicMock(total_tokens=100)
    return mock


@pytest.mark.asyncio
async def test_max_tool_calls_disables_tools_and_runs_last_round(
    mock_ctx,
):
    """測試 call_times >= max_tool_calls 時，工具會被停用，且會多跑一輪讓 AI 做最終回覆"""
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call_test",
        type="function",
        function=Function(name="test_tool", arguments="{}"),
    )

    # 10 輪有工具調用的 response，再接 1 輪無工具調用的最終回覆
    side_effects = [
        *[_make_response(f"tool_round_{i}", tool_calls=[tool_call]) for i in range(10)],
        _make_response("final_response"),
    ]

    with (
        patch("cmds.ai_chat.v2.chater.main.load_skills", return_value=None),
        patch(
            "cmds.ai_chat.v2.chater.main.get_openai_client",
            return_value=AsyncMock(
                chat=AsyncMock(
                    completions=AsyncMock(
                        create=AsyncMock(side_effect=side_effects)
                    )
                )
            ),
        ),
    ):
        chater = Chater(ctx=mock_ctx)
        response = await chater.chat(ctx=mock_ctx)

        # 最終回覆是最後一輪的內容
        assert response.result == "final_response"

        # history 應包含 10 個含工具調用的 assistant message
        # (最終回覆無工具調用，不會被寫入 history)
        assistant_messages = [m for m in response.infos.history if m.role == "assistant"]
        assert len(assistant_messages) == 10
        assert all(m.tool_calls is not None for m in assistant_messages)
