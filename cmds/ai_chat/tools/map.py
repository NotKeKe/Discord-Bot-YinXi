from cmds.ai_chat.tools.func import *
from cmds.ai_chat.tools.ai_func import *

tools = {
    # sync
    'calculate': calculate,
    'list_available_commands': list_available_commands,
    'current_time': current_time,
    'UnixToReadable': UnixToReadable,

    # async
    'web_search': web_search,
    'wiki_search': wiki_searh,
    'image_generate': image_generate,
    'video_generate': video_generate
}