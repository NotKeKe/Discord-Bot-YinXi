import pytest
from unittest.mock import AsyncMock, MagicMock
from motor.motor_asyncio import AsyncIOMotorClient

from cmds.bot_status import fetch_mongo_data


@pytest.fixture
def mock_coll():
    async def async_gen():
        yield {
            "_id": "1",
            "type": "custom",
            "name": "TOP_STATUS",
            "data": {"start_time": 1754562468.464611},
        }
        yield {
            "_id": "2",
            "type": "on_command",
            "name": "Command called times",
            "data": {"Load": {"restart": 682}},
            "total_times": 2953,
        }
        yield {
            "_id": "3",
            "type": "on_command",
            "name": "Command called times by a user",
            "data": {"703877871256731678": 2316},
        }

    class MockCursor:
        def __aiter__(self):
            return async_gen()

    coll = MagicMock()
    coll.find.return_value = MockCursor()
    return coll


@pytest.mark.asyncio
async def test_fetch_mongo_data(mock_coll, monkeypatch):
    monkeypatch.setattr("cmds.bot_status.coll", mock_coll)

    result = await fetch_mongo_data()

    assert result["top_status"]["name"] == "TOP_STATUS"
    assert result["command_called_times"]["name"] == "Command called times"
    assert result["command_called_by_user"]["name"] == "Command called times by a user"
