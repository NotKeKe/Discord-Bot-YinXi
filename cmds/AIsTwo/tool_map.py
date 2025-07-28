from cmds.AIsTwo.tools.tool_funcs import *

func_map = {
    'current_time': current_time,
    # 'discord_whereAmI': discord_whereAmI,
    # 'weather': weather,
    'calculate': calculate,
    'search': search,
    'image_generate': image_generate,
    'video_generate': video_generate,
    'UnixToReadable': UnixToReadable,
    'image_read': image_read,
    # 'knowledge_search': knowledge_base_search,
    # 'knowledge_save': knowledge_base_save,
    'wiki_search': wiki_searh,
    'list_available_commands': list_available_commands
}

tools_description_json_PATH = './cmds/AIsTwo/data/tools_descrip.json'
tools_descrip = read_json(tools_description_json_PATH)['tools']