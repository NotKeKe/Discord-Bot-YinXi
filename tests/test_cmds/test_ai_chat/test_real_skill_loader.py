from pathlib import Path

import pytest

from cmds.ai_chat.v2.tool.main import _load_one_skill

SKILLS_DIR = Path(__file__).parents[3] / "cmds" / "ai_chat" / "v2" / "tool" / "skills"

BOT_DEPENDENT = {"discord-command-list"}
NETWORK_DEPENDENT = {"web-search", "wiki-search"}


def _get_skill_paths():
    return sorted(SKILLS_DIR.rglob("SKILL.md"))


@pytest.mark.asyncio
async def test_load_all_real_skills():
    for skill_md in _get_skill_paths():
        name = skill_md.parent.name

        result = await _load_one_skill(skill_md)

        assert isinstance(result["name"], str) and result["name"]
        assert isinstance(result["description"], str) and result["description"]
        assert isinstance(result["content"], str)
        if name not in BOT_DEPENDENT | NETWORK_DEPENDENT:
            assert callable(result["function"]), f"{name}: function not callable"
        assert "function_as_openai_description" in result

        oai = result["function_as_openai_description"]
        assert oai["type"] == "function"
        assert oai["function"]["name"] == result["name"]
        assert oai["function"]["description"] == result["description"]
        assert isinstance(oai["function"]["parameters"], dict)


@pytest.mark.asyncio
async def test_calculate_skill():
    skill_md = SKILLS_DIR / "calculate" / "SKILL.md"
    result = await _load_one_skill(skill_md)

    assert result["name"] == "calculate"
    assert callable(result["function"])

    func = result["function"]
    assert func("1 + 2 * 3") == "7"
    assert func("10 / 2") == "5"
    assert func("7 % 3") == "1"
    assert func("2.5 * 4") == "10"
    assert func("1 / 0") == "無效的數學表達式"
    assert func("invalid syntax +++") == "無效的數學表達式"

    oai = result["function_as_openai_description"]
    assert "expression" in oai["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_current_time_skill():
    from datetime import datetime

    skill_md = SKILLS_DIR / "current-time" / "SKILL.md"
    result = await _load_one_skill(skill_md)

    assert result["name"] == "current-time"
    assert callable(result["function"])

    func = result["function"]
    time_str = func()
    parsed = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %z")
    assert parsed is not None

    time_str_tz1 = func(time_offset=1)
    parsed2 = datetime.strptime(time_str_tz1, "%Y-%m-%d %H:%M:%S %z")
    assert parsed2 is not None

    oai = result["function_as_openai_description"]
    assert "time_offset" in oai["function"]["parameters"]["properties"]
