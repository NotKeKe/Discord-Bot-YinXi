import orjson
from .map import tools as tool_map

with open('./cmds/ai_chat/tools/description.json', 'rb') as f:
    tool_description = orjson.loads(f.read())['tools']