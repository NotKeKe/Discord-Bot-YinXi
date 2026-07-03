import pytest

from cmds.ai_chat.v2.tool.main import _load_one_skill


@pytest.mark.asyncio
async def test_load_one_skill(tmp_path):
    skill_dir = tmp_path / "test-skill"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill\n"
        "---\n"
        "\n"
        "This is the skill content.\n",
        encoding="utf-8",
    )

    export_py = scripts_dir / "export.py"
    export_py.write_text(
        "class Tool:\n"
        "    def call(self, value: int = 0) -> int:\n"
        "        return value + 1\n",
        encoding="utf-8",
    )

    result = await _load_one_skill(skill_md)

    assert result["name"] == "test-skill"
    assert result["description"] == "A test skill"
    assert result["content"] == "This is the skill content."
    assert callable(result["function"])
    assert result["function"](5) == 6
