import importlib.util
from pathlib import Path
from typing import Any
import aiofiles
import frontmatter
import orjson

ALL_SKILLS = {}

async def _function_as_openai_description(skill_md_path: Path, name: str, description: str) -> dict:
    """將 function 轉為 openai 傳統工具的格式

    Args:
        name (str): _description_
        description (str): _description_
        function (_type_): _description_

    Returns:
        dict
    """   
    async with aiofiles.open(skill_md_path.parent / "tool.json", 'rb') as f:
        params = orjson.loads(await f.read())

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": params
        }
    }

async def _load_one_skill(skill_md_path: Path) -> dict:
    async with aiofiles.open(skill_md_path, 'r', encoding="utf-8") as f:
        raw = await f.read()

    skill = frontmatter.loads(raw)

    function = None
    export_path = skill_md_path.parent / "scripts" / "export.py"

    if export_path.exists() and export_path.is_file():
        module_name = f"tool_skill_{skill_md_path.parent.stem}"
        spec = importlib.util.spec_from_file_location(module_name, export_path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tool_class = getattr(module, "Tool", None)
            if tool_class is not None:
                function = getattr(tool_class(), "call", None)

    return {
        "name": skill.get("name", skill_md_path.stem), # 名稱
        "description": skill.get("description", ""), # 描述
        "content": skill.content, # 內文
        "function": function,
        "function_as_openai_description": await _function_as_openai_description(
            skill_md_path, 
            str(skill.get("name", skill_md_path.stem)), 
            str(skill.get("description", ""))
        ),
    }

async def _load_skills():
    for path in (Path(__file__).parent / "skills").rglob("SKILL.md"):
        skill = await _load_one_skill(path)
        ALL_SKILLS[skill["name"]] = skill