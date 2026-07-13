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


@pytest.fixture
def mock_openai_response():
    mock = MagicMock()
    mock.choices = [
        MagicMock(
            message=MagicMock(
                content="Hello!",
                tool_calls=None,
                reasoning_content=None,
                reasoning=None,
            )
        )
    ]
    mock.usage = MagicMock(total_tokens=50)
    return mock


@pytest.mark.asyncio
async def test_system_prompt_not_in_history(mock_ctx, mock_openai_response):
    """測試 system prompt 在對話完之後，是否還會出現在 history 當中 (應該要不存在)

    Args:
        mock_ctx (_type_): _description_
        mock_openai_response (_type_): _description_
    """    
    with (
        patch("cmds.ai_chat.v2.chater.main.load_skills", return_value=None),
        patch(
            "cmds.ai_chat.v2.chater.main.get_openai_client",
            return_value=AsyncMock(
                chat=AsyncMock(
                    completions=AsyncMock(
                        create=AsyncMock(return_value=mock_openai_response)
                    )
                )
            ),
        ),
    ):
        chater = Chater(ctx=mock_ctx)
        response = await chater.chat(ctx=mock_ctx)

        system_messages = [m for m in response.infos.history if m.role == "system"]
        assert len(system_messages) == 0
