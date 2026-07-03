import importlib.util
from pathlib import Path
from typing import Any
import aiofiles
import frontmatter

ALL_SKILLS = {}

async def _load_one_skill(path: Path) -> dict:
    async with aiofiles.open(path, 'r', encoding="utf-8") as f:
        f: Any = f
        raw = await f.read()

    skill = frontmatter.loads(raw)

    function = None
    export_path = path.parent / "scripts" / "export.py"

    if export_path.exists() and export_path.is_file():
        module_name = f"tool_skill_{path.parent.stem}"
        spec = importlib.util.spec_from_file_location(module_name, export_path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tool_class = getattr(module, "Tool", None)
            if tool_class is not None:
                function = getattr(tool_class(), "call", None)

    return {
        "name": skill.get("name", path.stem), # 名稱
        "description": skill.get("description", ""), # 描述
        "content": skill.content, # 內文
        "function": function,
    }

async def _load_skills():
    for path in Path("cmds/ai_chat/v2/tool/skill").glob("SKILL.md"):
        skill = await _load_one_skill(path)
        ALL_SKILLS[skill["name"]] = skill