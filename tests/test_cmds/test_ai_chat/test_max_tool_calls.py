import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord.ext import commands

# Prevent real clients module from executing at import time
fake_clients = MagicMock()
fake_clients.get_openai_client = MagicMock()
sys.modules["cmds.ai_chat.v2.data_keeper.clients"] = fake_clients

# Prevent real v1 tools from loading
sys.modules["cmds.ai_chat.v1.tools"] = MagicMock(tool_map={"test_tool": MagicMock()})

from cmds.ai_chat.v2.chater.main import Chater


class _AsyncIter:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


def _make_chunk(content="", tool_calls=None, finish_reason="stop"):
    delta = MagicMock(content=content or None, tool_calls=tool_calls)
    delta.reasoning_content = None

    chunk = MagicMock()
    chunk.choices = [MagicMock(delta=delta, finish_reason=finish_reason)]
    chunk.usage = MagicMock(total_tokens=100)
    return chunk


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


@pytest.mark.asyncio
async def test_max_tool_calls_disables_tools_and_runs_last_round(mock_ctx):
    """測試 call_times >= max_tool_calls 時，工具會被停用，且會多跑一輪讓 AI 做最終回覆"""
    tool_call = MagicMock()
    tool_call.index = 0
    tool_call.id = "call_test"
    tool_call.type = "function"

    func = MagicMock()
    func.name = "test_tool"
    func.arguments = "{}"
    tool_call.function = func

    tool_streams = [
        _AsyncIter([_make_chunk(tool_calls=[tool_call], finish_reason="tool_calls")])
        for _ in range(10)
    ]
    final_stream = _AsyncIter([_make_chunk(content="final_response")])

    side_effects = [*tool_streams, final_stream]

    with (
        patch("cmds.ai_chat.v2.chater.main.load_skills", return_value=None),
        patch(
            "cmds.ai_chat.v2.chater.main.get_openai_client",
            return_value=MagicMock(
                chat=MagicMock(
                    completions=MagicMock(
                        create=AsyncMock(side_effect=side_effects)
                    )
                )
            ),
        ),
    ):
        chater = Chater(ctx=mock_ctx)
        response = await chater.chat(ctx=mock_ctx)

        assert response.result == "final_response"

        system_messages = [m for m in response.infos.history if m.role == "system"]
        assert len(system_messages) == 0

        assistant_messages = [m for m in response.infos.history if m.role == "assistant"]
        assert len(assistant_messages) == 11
        assert len([m for m in assistant_messages if m.tool_calls is not None]) == 10
        assert assistant_messages[-1].tool_calls is None
