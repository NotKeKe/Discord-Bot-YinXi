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
    # prevent MagicMock auto-creating child mocks for these attributes
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
async def test_system_prompt_not_in_history(mock_ctx):
    """測試 system prompt 在對話完之後，是否還會出現在 history 當中 (應該要不存在)"""
    stream = _AsyncIter([_make_chunk(content="Hello!")])

    with (
        patch("cmds.ai_chat.v2.chater.main.load_skills", return_value=None),
        patch(
            "cmds.ai_chat.v2.chater.main.get_openai_client",
            return_value=MagicMock(
                chat=MagicMock(
                    completions=MagicMock(
                        create=AsyncMock(return_value=stream)
                    )
                )
            ),
        ),
    ):
        chater = Chater(ctx=mock_ctx)
        response = await chater.chat(ctx=mock_ctx)

        system_messages = [m for m in response.infos.history if m.role == "system"]
        assert len(system_messages) == 0
